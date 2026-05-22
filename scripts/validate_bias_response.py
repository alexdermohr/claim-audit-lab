#!/usr/bin/env python3
"""Validate bias responses against machine-derived bias signals.

Bias signals are generated from case artifacts (scripts/generate_bias_signals.py).
This validator checks that, before finalization, every required signal has a
response that points at concrete artifacts. See docs/bias-signal-discipline.md.

Draft-mode cases may carry open signals; final-mode cases may not.
"""

from __future__ import annotations

import json
import pathlib
import sys

from jsonschema_compat import jsonschema
import yaml

import generate_bias_signals as gbs
from case_compat import legacy_case_error

RESPONSE_SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "bias-response.v1.schema.json"
RESPONSE_FILENAME = "bias-response.yml"

# Statuses that mean "this assessment is finalized" and so gate hard.
FINAL_STATUSES = {"assessed", "final_under_uncertainty"}
SEVERE_THRESHOLD = 0.75
# Severe signals may not be discharged by mere acceptance.
SEVERE_ALLOWED_STATUSES = {"mitigated", "false_positive", "escalated_to_redteam"}


def _load_yaml(path: pathlib.Path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except Exception as exc:
        return None, str(exc)


def load_schema(path: pathlib.Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def schema_errors(payload: dict, schema: dict) -> list[str]:
    validator = jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())
    return [
        f"Schema error at {list(error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda err: list(err.absolute_path))
    ]


def _lifecycle_status(case_dir: pathlib.Path) -> str:
    data, _ = _load_yaml(case_dir / "lifecycle.yml")
    if isinstance(data, dict):
        return str(data.get("status", ""))
    return ""


def _ref_exists(case_dir: pathlib.Path, ref: str) -> bool:
    """A response ref points at an existing file inside the case directory.

    An optional #anchor is ignored. Absolute paths, ``..`` escapes, empty refs,
    and directory refs (e.g. ``"."`` or ``"./"``) are all rejected.
    """
    target = ref.split("#", 1)[0].strip()
    if not target:
        return False
    if pathlib.Path(target).is_absolute():
        return False
    base = case_dir.resolve()
    resolved = (case_dir / target).resolve()
    try:
        resolved.relative_to(base)
    except ValueError:
        return False
    return resolved.exists() and resolved.is_file()


class CaseResult:
    def __init__(self, case_dir: pathlib.Path):
        self.case_dir = case_dir
        self.errors: list[str] = []
        self.warnings: list[str] = []


def _validate_required_coverage(signals: list[dict], by_ref: dict[str, dict], result: CaseResult) -> None:
    responded = set(by_ref)
    for signal in signals:
        if signal.get("required_response") and signal["signal_id"] not in responded:
            result.errors.append(
                f"required signal {signal['signal_id']} ({signal['signal_type']}, "
                f"severity {signal['severity']}) has no response."
            )


def _validate_one_response(
    case_dir: pathlib.Path,
    response: dict,
    signal: dict,
    result: CaseResult,
) -> None:
    status = response.get("response_status")
    signal_ref = response.get("signal_ref")
    severity = signal.get("severity", 0.0)
    refs = [r for r in (response.get("mitigation_refs") or []) if isinstance(r, str)]
    existing_refs = [r for r in refs if _ref_exists(case_dir, r)]

    if status == "mitigated":
        if not existing_refs:
            result.errors.append(
                f"response to {signal_ref} is 'mitigated' but has no existing mitigation_refs artifact."
            )
    elif status == "accepted_with_constraint":
        if not isinstance(response.get("residual_risk"), (int, float)) or isinstance(response.get("residual_risk"), bool):
            result.errors.append(
                f"response to {signal_ref} is 'accepted_with_constraint' but lacks a numeric residual_risk."
            )
        if not str(response.get("constraint_statement", "") or "").strip():
            result.errors.append(
                f"response to {signal_ref} is 'accepted_with_constraint' but lacks a constraint_statement."
            )
        if not existing_refs:
            result.errors.append(
                f"response to {signal_ref} is 'accepted_with_constraint' but cites no existing artifact ref."
            )
    elif status == "false_positive":
        if not existing_refs:
            result.errors.append(
                f"response to {signal_ref} is 'false_positive' but cites no existing artifact ref to back it."
            )
    elif status == "escalated_to_redteam":
        redteam_ref = str(response.get("redteam_ref", "") or "").strip()
        if not redteam_ref:
            result.errors.append(
                f"response to {signal_ref} is 'escalated_to_redteam' but lacks a redteam_ref."
            )
        elif not _ref_exists(case_dir, redteam_ref):
            result.errors.append(
                f"response to {signal_ref} escalates to a non-existent redteam_ref '{redteam_ref}'."
            )

    if severity >= SEVERE_THRESHOLD and status not in SEVERE_ALLOWED_STATUSES:
        result.errors.append(
            f"severe signal {signal_ref} (severity {severity}) cannot be discharged by "
            f"'{status}'; use one of {sorted(SEVERE_ALLOWED_STATUSES)}."
        )


def validate_case(case_dir: pathlib.Path, response_schema: dict) -> CaseResult:
    result = CaseResult(case_dir)

    legacy_error = legacy_case_error(case_dir)
    if legacy_error:
        result.errors.append(legacy_error)
        return result

    status = _lifecycle_status(case_dir)
    is_final = status in FINAL_STATUSES

    signals = gbs.generate_for_case(case_dir)
    signals_by_id = {s["signal_id"]: s for s in signals}

    response_path = case_dir / RESPONSE_FILENAME
    response_doc = None
    if response_path.exists():
        response_doc, err = _load_yaml(response_path)
        if err:
            result.errors.append(f"Could not parse {RESPONSE_FILENAME}: {err}")
            return result
        if not isinstance(response_doc, dict):
            result.errors.append(f"{RESPONSE_FILENAME} must contain a YAML object.")
            return result
        # Malformed responses fail in every mode; schema is binding everywhere.
        errs = schema_errors(response_doc, response_schema)
        if errs:
            result.errors.extend(f"{RESPONSE_FILENAME}: {e}" for e in errs)
            return result

        # case_ref must match the case directory this file lives in.
        expected_ref = gbs.relative_case_ref(case_dir)
        doc_ref = response_doc.get("case_ref", "")
        if doc_ref != expected_ref:
            result.errors.append(
                f"bias-response.yml case_ref '{doc_ref}' does not match "
                f"expected '{expected_ref}' for this case directory."
            )
            return result

    responses = []
    if isinstance(response_doc, dict):
        responses = [r for r in response_doc.get("responses", []) if isinstance(r, dict)]

    by_ref: dict[str, dict] = {}
    for response in responses:
        ref = response.get("signal_ref")
        if not isinstance(ref, str):
            continue
        by_ref[ref] = response
        if ref not in signals_by_id:
            message = (
                f"response references signal {ref} that was not generated for this case."
            )
            if is_final:
                result.errors.append(message)
            else:
                result.warnings.append(message)

    if not is_final:
        open_required = sum(
            1 for s in signals if s.get("required_response") and s["signal_id"] not in by_ref
        )
        if open_required:
            result.warnings.append(
                f"draft mode: {open_required} required signal(s) still open (allowed in draft)."
            )
        return result

    # Final mode: full coverage required.
    _validate_required_coverage(signals, by_ref, result)
    for ref, response in by_ref.items():
        signal = signals_by_id.get(ref)
        if signal is None:
            continue  # already reported as an error above
        _validate_one_response(case_dir, response, signal, result)

    return result


def discover_case_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(
        {
            marker.parent
            for marker in root.rglob("claims.yml")
            if "_template" not in marker.parts and gbs.GENERATED_SUBDIR not in marker.parts
        }
    )


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    response_schema = load_schema(RESPONSE_SCHEMA_PATH)
    case_dirs = discover_case_dirs(root)
    if not case_dirs:
        print(f"No case directories found under {root}")
        return 0

    total_errors = 0
    for case_dir in case_dirs:
        result = validate_case(case_dir, response_schema)
        if result.errors:
            print(f"FAIL {case_dir}:")
            for err in result.errors:
                print(f"  {err}")
            total_errors += len(result.errors)
        else:
            print(f"OK   {case_dir}")
        for warning in result.warnings:
            print(f"  warning: {warning}")

    if total_errors:
        print(f"\n{total_errors} bias-response error(s) found.")
        return 1
    print("\nAll bias responses valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
