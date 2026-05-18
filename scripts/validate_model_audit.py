#!/usr/bin/env python3
"""Validate case-local model-audit.yml artifacts."""

from collections import Counter
import json
import pathlib
import sys

from jsonschema_compat import jsonschema
import yaml

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "model-audit.v1.schema.json"


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


def collect_refs(case_dir: pathlib.Path) -> tuple[set[str] | None, set[str] | None, set[str] | None, list[str]]:
    errors: list[str] = []
    claims_data, load_errors = load_optional_object(case_dir / "claims.yml", "claims.yml")
    errors.extend(load_errors)
    hypotheses_data, load_errors = load_optional_object(case_dir / "hypotheses.yml", "hypotheses.yml")
    errors.extend(load_errors)
    defeaters_data, load_errors = load_optional_object(case_dir / "model-defeaters.yml", "model-defeaters.yml")
    errors.extend(load_errors)

    claim_ids: set[str] | None = None
    if claims_data is not None:
        claims = require_list(claims_data, "claims", "claims.yml", errors)
        claim_ids = {
            item.get("claim_id") for item in claims
            if isinstance(item, dict) and isinstance(item.get("claim_id"), str)
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

    defeater_ids: set[str] | None = None
    if defeaters_data is not None:
        defeaters = require_list(defeaters_data, "defeaters", "model-defeaters.yml", errors)
        defeater_ids = {
            item.get("defeater_id") for item in defeaters
            if isinstance(item, dict) and isinstance(item.get("defeater_id"), str)
        }

    return claim_ids, hypothesis_ids, defeater_ids, errors


def validate_case(case_dir: pathlib.Path, schema: dict) -> list[str]:
    path = case_dir / "model-audit.yml"
    if not path.exists():
        return []

    errors: list[str] = []
    data, err = safe_load_yaml(path)
    if err:
        return [f"Could not parse model-audit.yml: {err}"]
    if not isinstance(data, dict):
        return ["model-audit.yml must contain a YAML object."]

    errors.extend(schema_errors(data, schema))
    models = require_list(data, "models", "model-audit.yml", errors)

    ids = [m.get("model_id") for m in models if isinstance(m, dict) and isinstance(m.get("model_id"), str)]
    for model_id, count in Counter(ids).items():
        if count > 1:
            errors.append(f"duplicate model_id '{model_id}'.")

    claim_ids, hypothesis_ids, defeater_ids, load_errors = collect_refs(case_dir)
    errors.extend(load_errors)

    for model in models:
        if not isinstance(model, dict):
            continue
        model_id = model.get("model_id", "?")

        claim_ref = model.get("claim_ref")
        if isinstance(claim_ref, str) and claim_ids is not None and claim_ref not in claim_ids:
            errors.append(f"model '{model_id}' claim_ref '{claim_ref}' not found in claims.yml.")

        hypothesis_ref = model.get("hypothesis_ref")
        if isinstance(hypothesis_ref, str) and hypothesis_ids is not None and hypothesis_ref not in hypothesis_ids:
            errors.append(f"model '{model_id}' hypothesis_ref '{hypothesis_ref}' not found in hypotheses.yml.")

        refs = model.get("unresolved_defeater_refs")
        if isinstance(refs, list):
            for index, ref in enumerate(refs):
                if not isinstance(ref, str):
                    errors.append(f"model '{model_id}' unresolved_defeater_refs[{index}] must be a string.")
                    continue
                if defeater_ids is not None and ref not in defeater_ids:
                    errors.append(f"model '{model_id}' unresolved_defeater_ref '{ref}' not found in model-defeaters.yml.")

    return errors


def discover_case_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted({marker.parent for marker in root.rglob("model-audit.yml") if "_template" not in marker.parts})


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    schema = load_schema()
    case_dirs = discover_case_dirs(root)
    if not case_dirs:
        print(f"No model-audit.yml files found under {root}")
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
        print(f"\n{total_errors} model-audit error(s) found.")
        return 1
    print("\nAll model audits valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
