#!/usr/bin/env python3
"""Validate contradictions.yml and conflict-ledger expectations."""

from collections import Counter
import json
import pathlib
import sys

from jsonschema_compat import jsonschema
import yaml

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "contradictions.v1.schema.json"
CLOSURE_STATUSES = {"assessed", "provisional_under_uncertainty", "final_under_uncertainty"}
CASE_MARKERS = {"claims.yml", "contradictions.yml", "lifecycle.yml", "assessment.md"}


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


def lifecycle_status(case_dir: pathlib.Path, errors: list[str]) -> str | None:
    data, load_errors = load_optional_object(case_dir / "lifecycle.yml", "lifecycle.yml")
    errors.extend(load_errors)
    if not isinstance(data, dict):
        return None
    status = data.get("status")
    if status is not None and not isinstance(status, str):
        errors.append("lifecycle.yml status must be a string.")
        return None
    return status


def claim_ids_and_counterclaim_flag(case_dir: pathlib.Path, errors: list[str]) -> tuple[set[str], bool]:
    data, load_errors = load_optional_object(case_dir / "claims.yml", "claims.yml")
    errors.extend(load_errors)
    if not isinstance(data, dict):
        return set(), False
    claims = data.get("claims", [])
    if not isinstance(claims, list):
        errors.append("claims.yml 'claims' must be an array.")
        return set(), False
    claim_ids: set[str] = set()
    has_counterclaims = False
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            errors.append(f"claims.yml claims[{index}] must be an object.")
            continue
        claim_id = claim.get("claim_id")
        if isinstance(claim_id, str):
            claim_ids.add(claim_id)
        elif claim_id is not None:
            errors.append(f"claims.yml claims[{index}].claim_id must be a string.")
        counterclaims = claim.get("counterclaims", [])
        if counterclaims:
            if not isinstance(counterclaims, list):
                errors.append(f"claim '{claim_id or index}' counterclaims must be an array.")
            else:
                has_counterclaims = True
    return claim_ids, has_counterclaims


def validate_contradictions_file(data: dict, schema: dict, claim_ids: set[str]) -> list[str]:
    errors = schema_errors(data, schema)
    contradictions = data.get("contradictions", []) if isinstance(data.get("contradictions", []), list) else []
    ids = []
    for index, contradiction in enumerate(contradictions):
        if not isinstance(contradiction, dict):
            continue
        contradiction_id = contradiction.get("contradiction_id")
        if isinstance(contradiction_id, str):
            ids.append(contradiction_id)
        for key in ("claim_a_ref", "claim_b_ref"):
            claim_ref = contradiction.get(key)
            if isinstance(claim_ref, str) and claim_ref not in claim_ids:
                errors.append(
                    f"contradiction '{contradiction_id or '?'}' {key} '{claim_ref}' not found in claims.yml."
                )
        if contradiction.get("resolution_status") and not str(contradiction.get("resolution_notes", "")).strip():
            errors.append(
                f"contradiction '{contradiction_id or '?'}' must include resolution_notes; contradictions document conflicts and do not alter verdicts by existence alone."
            )
    for contradiction_id, count in Counter(ids).items():
        if count > 1:
            errors.append(f"duplicate contradiction_id '{contradiction_id}'.")
    return errors


def validate_case(case_dir: pathlib.Path, schema: dict | None = None) -> list[str]:
    schema = schema or load_schema()
    errors: list[str] = []
    claim_ids, has_counterclaims = claim_ids_and_counterclaim_flag(case_dir, errors)
    status = lifecycle_status(case_dir, errors)
    contradictions_path = case_dir / "contradictions.yml"

    if status in CLOSURE_STATUSES and has_counterclaims and not contradictions_path.exists():
        errors.append(
            "contradictions.yml required for assessed/provisional/final cases with counterclaims; conflicts must be artifact-visible, not only assessment prose."
        )

    if contradictions_path.exists():
        data, load_error = safe_load_yaml(contradictions_path)
        if load_error:
            errors.append(f"Could not parse contradictions.yml: {load_error}")
        elif not isinstance(data, dict):
            errors.append("contradictions.yml must contain a YAML object.")
        else:
            errors.extend(validate_contradictions_file(data, schema, claim_ids))
    return errors


def is_case_dir(path: pathlib.Path) -> bool:
    return any((path / marker).exists() for marker in CASE_MARKERS)


def discover_case_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    candidate_dirs = {root}
    for marker in CASE_MARKERS:
        candidate_dirs.update(path.parent for path in root.rglob(marker))
    return sorted(d for d in candidate_dirs if d.is_dir() and "_template" not in d.parts and is_case_dir(d))


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    schema = load_schema()
    case_dirs = discover_case_dirs(root)
    if not case_dirs:
        print(f"No contradiction case directories found under {root}")
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
        print(f"\n{total_errors} contradiction error(s) found.")
        return 1
    print("\nAll contradiction ledgers valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
