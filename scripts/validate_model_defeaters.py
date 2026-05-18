#!/usr/bin/env python3
"""Validate case-local model-defeaters.yml artifacts."""

from collections import Counter
import json
import pathlib
import sys

from jsonschema_compat import jsonschema
import yaml

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "model-defeaters.v1.schema.json"
HIGH_MATERIALITY = 0.75


def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def safe_load_yaml(path: pathlib.Path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except Exception as exc:
        return None, str(exc)


def load_optional_object(path: pathlib.Path, label: str) -> tuple[dict | None, list[str]]:
    if not path.exists():
        return None, []
    data, err = safe_load_yaml(path)
    if err:
        return None, [f"Could not parse {label}: {err}"]
    if not isinstance(data, dict):
        return None, [f"{label} must contain a YAML object."]
    return data, []


def schema_errors(payload: dict, schema: dict) -> list[str]:
    validator = jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())
    return [
        f"Schema error at {list(error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda err: list(err.absolute_path))
    ]


def require_list(data: dict, key: str, label: str, errors: list[str]) -> list:
    if key not in data:
        return []
    value = data.get(key)
    if not isinstance(value, list):
        errors.append(f"{label} '{key}' must be an array.")
        return []
    return value


def normalize_string_list(value, context: str) -> tuple[list[str], list[str]]:
    if value is None:
        return [], []
    if not isinstance(value, list):
        return [], [f"{context} must be an array of strings."]
    result: list[str] = []
    errors: list[str] = []
    for index, item in enumerate(value):
        if isinstance(item, str):
            result.append(item)
        else:
            errors.append(f"{context}[{index}] must be a string.")
    return result, errors


def collect_refs(case_dir: pathlib.Path) -> tuple[set[str] | None, set[str] | None, set[str] | None, set[str] | None, list[str]]:
    errors: list[str] = []
    claims_data, load_errors = load_optional_object(case_dir / "claims.yml", "claims.yml")
    errors.extend(load_errors)
    sources_data, load_errors = load_optional_object(case_dir / "sources.yml", "sources.yml")
    errors.extend(load_errors)
    hypotheses_data, load_errors = load_optional_object(case_dir / "hypotheses.yml", "hypotheses.yml")
    errors.extend(load_errors)
    evidence_data, load_errors = load_optional_object(case_dir / "evidence-pack.yml", "evidence-pack.yml")
    errors.extend(load_errors)

    claim_ids: set[str] | None = None
    if claims_data is not None:
        claims = require_list(claims_data, "claims", "claims.yml", errors)
        claim_ids = {
            item.get("claim_id") for item in claims
            if isinstance(item, dict) and isinstance(item.get("claim_id"), str)
        }

    source_ids: set[str] | None = None
    if sources_data is not None:
        sources = require_list(sources_data, "sources", "sources.yml", errors)
        source_ids = {
            item.get("source_id") for item in sources
            if isinstance(item, dict) and isinstance(item.get("source_id"), str)
        }

    hypothesis_ids: set[str] | None = None
    if hypotheses_data is not None:
        hypotheses = require_list(hypotheses_data, "hypotheses", "hypotheses.yml", errors)
        hypothesis_ids = set()
        for item in hypotheses:
            if not isinstance(item, dict):
                continue
            for key in ("id", "hypothesis_id"):
                value = item.get(key)
                if isinstance(value, str):
                    hypothesis_ids.add(value)

    evidence_ids: set[str] | None = None
    if evidence_data is not None:
        evidence = require_list(evidence_data, "evidence", "evidence-pack.yml", errors)
        evidence_ids = {
            item.get("evidence_id") for item in evidence
            if isinstance(item, dict) and isinstance(item.get("evidence_id"), str)
        }

    return claim_ids, source_ids, hypothesis_ids, evidence_ids, errors


def validate_case(case_dir: pathlib.Path, schema: dict) -> list[str]:
    path = case_dir / "model-defeaters.yml"
    if not path.exists():
        return []

    errors: list[str] = []
    data, err = safe_load_yaml(path)
    if err:
        return [f"Could not parse model-defeaters.yml: {err}"]
    if not isinstance(data, dict):
        return ["model-defeaters.yml must contain a YAML object."]

    errors.extend(schema_errors(data, schema))
    defeaters = require_list(data, "defeaters", "model-defeaters.yml", errors)

    ids = [d.get("defeater_id") for d in defeaters if isinstance(d, dict) and isinstance(d.get("defeater_id"), str)]
    for defeater_id, count in Counter(ids).items():
        if count > 1:
            errors.append(f"duplicate defeater_id '{defeater_id}'.")

    claim_ids, source_ids, hypothesis_ids, evidence_ids, load_errors = collect_refs(case_dir)
    errors.extend(load_errors)

    for defeater in defeaters:
        if not isinstance(defeater, dict):
            continue
        defeater_id = defeater.get("defeater_id", "?")

        target_claim = defeater.get("target_claim_ref")
        target_hypothesis = defeater.get("target_hypothesis_ref")
        target_step = defeater.get("target_chain_step")
        targets = [str(t).strip() for t in (target_claim, target_hypothesis, target_step) if isinstance(t, str)]
        if not any(targets):
            errors.append(
                f"defeater '{defeater_id}' must target at least one of target_claim_ref, target_hypothesis_ref, or target_chain_step."
            )

        if isinstance(target_claim, str) and target_claim and claim_ids is not None and target_claim not in claim_ids:
            errors.append(f"defeater '{defeater_id}' target_claim_ref '{target_claim}' not found in claims.yml.")
        if isinstance(target_hypothesis, str) and target_hypothesis and hypothesis_ids is not None and target_hypothesis not in hypothesis_ids:
            errors.append(f"defeater '{defeater_id}' target_hypothesis_ref '{target_hypothesis}' not found in hypotheses.yml.")

        source_refs, ref_errors = normalize_string_list(defeater.get("source_refs"), f"defeater '{defeater_id}' source_refs")
        errors.extend(ref_errors)
        if source_ids is not None:
            for ref in source_refs:
                if ref not in source_ids:
                    errors.append(f"defeater '{defeater_id}' source_ref '{ref}' not found in sources.yml.")

        evidence_refs, ref_errors = normalize_string_list(defeater.get("evidence_refs"), f"defeater '{defeater_id}' evidence_refs")
        errors.extend(ref_errors)
        if evidence_ids is not None:
            for ref in evidence_refs:
                if ref not in evidence_ids:
                    errors.append(f"defeater '{defeater_id}' evidence_ref '{ref}' not found in evidence-pack.yml.")

        rebuttal_refs, ref_errors = normalize_string_list(defeater.get("rebuttal_evidence_refs"), f"defeater '{defeater_id}' rebuttal_evidence_refs")
        errors.extend(ref_errors)
        if evidence_ids is not None:
            for ref in rebuttal_refs:
                if ref not in evidence_ids:
                    errors.append(f"defeater '{defeater_id}' rebuttal_evidence_ref '{ref}' not found in evidence-pack.yml.")

        materiality = defeater.get("materiality")
        status = defeater.get("status")
        if isinstance(materiality, (int, float)) and materiality >= HIGH_MATERIALITY and status in ("resolved", "partially_resolved"):
            if not rebuttal_refs:
                errors.append(
                    f"high-materiality defeater '{defeater_id}' marked '{status}' requires at least one rebuttal_evidence_ref."
                )

    return errors


def discover_case_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted({marker.parent for marker in root.rglob("model-defeaters.yml") if "_template" not in marker.parts})


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    schema = load_schema()
    case_dirs = discover_case_dirs(root)
    if not case_dirs:
        print(f"No model-defeaters.yml files found under {root}")
        return 0

    total_errors = 0
    for case_dir in case_dirs:
        errors = validate_case(case_dir, schema)
        if errors:
            print(f"FAIL {case_dir}:")
            for error in errors:
                print(f"  {error}")
            total_errors += len(errors)
        else:
            print(f"OK   {case_dir}")

    if total_errors:
        print(f"\n{total_errors} model-defeater error(s) found.")
        return 1
    print("\nAll model defeaters valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
