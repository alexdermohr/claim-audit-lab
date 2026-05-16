#!/usr/bin/env python3
"""Validate case-local anomaly-ledger.yml artifacts."""

import json
import pathlib
import sys
from collections import Counter

from jsonschema_compat import jsonschema
import yaml

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "anomaly-ledger.v1.schema.json"
HIGH_MATERIALITY = 0.7


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


def nonempty_list(value) -> bool:
    return isinstance(value, list) and any(str(item).strip() for item in value)


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


def collect_ids(case_dir: pathlib.Path) -> tuple[set[str] | None, set[str] | None, set[str] | None, list[str]]:
    errors: list[str] = []
    claims_data, load_errors = load_optional_object(case_dir / "claims.yml", "claims.yml")
    errors.extend(load_errors)
    sources_data, load_errors = load_optional_object(case_dir / "sources.yml", "sources.yml")
    errors.extend(load_errors)
    hypotheses_data, load_errors = load_optional_object(case_dir / "hypotheses.yml", "hypotheses.yml")
    errors.extend(load_errors)

    claim_ids = None
    if claims_data is not None:
        claims = require_list(claims_data, "claims", "claims.yml", errors)
        claim_ids = {
            item.get("claim_id")
            for item in claims
            if isinstance(item, dict) and isinstance(item.get("claim_id"), str)
        }

    source_ids = None
    if sources_data is not None:
        sources = require_list(sources_data, "sources", "sources.yml", errors)
        source_ids = {
            item.get("source_id")
            for item in sources
            if isinstance(item, dict) and isinstance(item.get("source_id"), str)
        }

    hypothesis_ids = None
    if hypotheses_data is not None:
        hypotheses = require_list(hypotheses_data, "hypotheses", "hypotheses.yml", errors)
        hypothesis_ids = {
            item.get("id") if isinstance(item.get("id"), str) else item.get("hypothesis_id")
            for item in hypotheses
            if isinstance(item, dict) and (isinstance(item.get("id"), str) or isinstance(item.get("hypothesis_id"), str))
        }

    return claim_ids, source_ids, hypothesis_ids, errors


def validate_case(case_dir: pathlib.Path, schema: dict) -> list[str]:
    ledger_path = case_dir / "anomaly-ledger.yml"
    if not ledger_path.exists():
        return []

    errors: list[str] = []
    data, err = safe_load_yaml(ledger_path)
    if err:
        return [f"Could not parse anomaly-ledger.yml: {err}"]
    if not isinstance(data, dict):
        return ["anomaly-ledger.yml must contain a YAML object."]

    errors.extend(schema_errors(data, schema))
    anomalies = require_list(data, "anomalies", "anomaly-ledger.yml", errors)

    ids = [item.get("anomaly_id") for item in anomalies if isinstance(item, dict) and isinstance(item.get("anomaly_id"), str)]
    for anomaly_id, count in Counter(ids).items():
        if count > 1:
            errors.append(f"duplicate anomaly_id '{anomaly_id}'.")

    claim_ids, source_ids, hypothesis_ids, load_errors = collect_ids(case_dir)
    errors.extend(load_errors)

    for anomaly in anomalies:
        if not isinstance(anomaly, dict):
            continue
        anomaly_id = anomaly.get("anomaly_id", "?")
        source_refs, ref_errors = normalize_string_list(anomaly.get("source_refs"), f"anomaly '{anomaly_id}' source_refs")
        errors.extend(ref_errors)
        if source_ids is not None:
            for source_ref in source_refs:
                if source_ref not in source_ids:
                    errors.append(f"anomaly '{anomaly_id}' source_ref '{source_ref}' not found in sources.yml.")

        affected_claims, ref_errors = normalize_string_list(anomaly.get("affected_claims"), f"anomaly '{anomaly_id}' affected_claims")
        errors.extend(ref_errors)
        if claim_ids is not None:
            for claim_ref in affected_claims:
                if claim_ref not in claim_ids:
                    errors.append(f"anomaly '{anomaly_id}' affected_claim '{claim_ref}' not found in claims.yml.")

        affected_hypotheses, ref_errors = normalize_string_list(
            anomaly.get("affected_hypotheses"),
            f"anomaly '{anomaly_id}' affected_hypotheses",
        )
        errors.extend(ref_errors)
        if hypothesis_ids is not None:
            for hypothesis_ref in affected_hypotheses:
                if hypothesis_ref not in hypothesis_ids:
                    errors.append(
                        f"anomaly '{anomaly_id}' affected_hypothesis '{hypothesis_ref}' not found in hypotheses.yml."
                    )

        verdict_effect = anomaly.get("verdict_effect")
        if isinstance(verdict_effect, dict) and claim_ids is not None:
            claim_ref = verdict_effect.get("claim_ref")
            if claim_ref is not None and not isinstance(claim_ref, str):
                errors.append(f"anomaly '{anomaly_id}' verdict_effect.claim_ref must be a string.")
            elif claim_ref and claim_ref not in claim_ids:
                errors.append(f"anomaly '{anomaly_id}' verdict_effect claim_ref '{claim_ref}' not found in claims.yml.")

        materiality = anomaly.get("materiality")
        if isinstance(materiality, (int, float)) and materiality >= HIGH_MATERIALITY:
            if not str(anomaly.get("why_it_matters", "")).strip():
                errors.append(f"high-materiality anomaly '{anomaly_id}' requires why_it_matters.")
            if not nonempty_list(anomaly.get("possible_benign_explanations")):
                errors.append(
                    f"high-materiality anomaly '{anomaly_id}' requires at least one possible_benign_explanations item."
                )
            if not nonempty_list(anomaly.get("possible_bias_explanations")):
                errors.append(
                    f"high-materiality anomaly '{anomaly_id}' requires at least one possible_bias_explanations item; this documents hypotheses, not proof of bias."
                )
            if not nonempty_list(anomaly.get("missing_for_resolution")):
                errors.append(f"high-materiality anomaly '{anomaly_id}' requires at least one missing_for_resolution item.")
            if not isinstance(verdict_effect, dict):
                errors.append(f"high-materiality anomaly '{anomaly_id}' requires verdict_effect.")

    return errors


def discover_case_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted({marker.parent for marker in root.rglob("anomaly-ledger.yml") if "_template" not in marker.parts})


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    schema = load_schema()
    case_dirs = discover_case_dirs(root)
    if not case_dirs:
        print(f"No anomaly-ledger.yml files found under {root}")
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
        print(f"\n{total_errors} anomaly-ledger error(s) found.")
        return 1
    print("\nAll anomaly ledgers valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
