#!/usr/bin/env python3
"""Validate investigation-integrity.yml and closure-power source coverage."""

import json
import pathlib
import sys
from collections import Counter

from jsonschema_compat import jsonschema
import yaml

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "investigation-integrity.v1.schema.json"
RISK_THRESHOLD = 0.6
ADVERSARIAL_THRESHOLD = 0.7
CLOSURE_SENSITIVE_SOURCE_TYPES = {
    "government_report",
    "official_body",
    "corporate_report",
    "ngo_report",
    "advocacy_report",
}
STRONG_STATUSES = {"established", "strongly_supported", "contradicted"}
REPORTED_CLAIM_KIND = "reported_claim"
CASE_MARKERS = {"sources.yml", "claims.yml", "evidence-pack.yml", "investigation-integrity.yml"}


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


def source_weight_value(source: dict, key: str) -> float | None:
    raw = None
    if isinstance(source.get("source_weight"), dict):
        raw = source["source_weight"].get(key)
    if raw is None:
        raw = source.get(key)
    if isinstance(raw, (int, float)):
        return float(raw)
    return None


def strong_world_claims_using_sources(claims_data: dict | None, evidence_data: dict | None) -> dict[str, set[str]]:
    if not isinstance(claims_data, dict):
        return {}

    evidence_source_by_id = {}
    if isinstance(evidence_data, dict):
        for evidence in evidence_data.get("evidence", []) or []:
            if isinstance(evidence, dict) and evidence.get("evidence_id") and evidence.get("source_ref"):
                evidence_source_by_id[evidence["evidence_id"]] = evidence["source_ref"]

    claims_by_source: dict[str, set[str]] = {}
    for claim in claims_data.get("claims", []) or []:
        if not isinstance(claim, dict):
            continue
        claim_id = claim.get("claim_id")
        if not claim_id or claim.get("status") not in STRONG_STATUSES:
            continue
        if claim.get("claim_kind") == REPORTED_CLAIM_KIND:
            continue
        source_refs = set(claim.get("source_refs") or [])
        for evidence_ref in claim.get("evidence_refs") or []:
            if evidence_ref in evidence_source_by_id:
                source_refs.add(evidence_source_by_id[evidence_ref])
        for source_ref in source_refs:
            claims_by_source.setdefault(source_ref, set()).add(claim_id)
    return claims_by_source


def validate_integrity_file(data: dict, schema: dict, source_ids: set[str] | None) -> tuple[list[str], set[str]]:
    errors = schema_errors(data, schema)
    investigations = data.get("investigations", []) if isinstance(data.get("investigations", []), list) else []

    ids = [item.get("investigation_id") for item in investigations if isinstance(item, dict) and item.get("investigation_id")]
    for investigation_id, count in Counter(ids).items():
        if count > 1:
            errors.append(f"duplicate investigation_id '{investigation_id}'.")

    covered_sources: set[str] = set()
    for investigation in investigations:
        if not isinstance(investigation, dict):
            continue
        investigation_id = investigation.get("investigation_id", "?")
        for source_ref in investigation.get("source_cluster_refs") or []:
            covered_sources.add(source_ref)
            if source_ids is not None and source_ref not in source_ids:
                errors.append(
                    f"investigation '{investigation_id}' source_cluster_ref '{source_ref}' not found in sources.yml."
                )
        paths = investigation.get("non_tested_material_paths")
        if paths is not None and not isinstance(paths, list):
            errors.append(f"investigation '{investigation_id}' non_tested_material_paths must be a list.")
    return errors, covered_sources


def validate_case(case_dir: pathlib.Path, schema: dict) -> list[str]:
    errors: list[str] = []
    sources_data, load_errors = load_optional_object(case_dir / "sources.yml", "sources.yml")
    errors.extend(load_errors)
    claims_data, load_errors = load_optional_object(case_dir / "claims.yml", "claims.yml")
    errors.extend(load_errors)
    evidence_data, load_errors = load_optional_object(case_dir / "evidence-pack.yml", "evidence-pack.yml")
    errors.extend(load_errors)

    source_ids: set[str] | None = None
    source_by_id: dict[str, dict] = {}
    if isinstance(sources_data, dict):
        source_by_id = {
            item.get("source_id"): item
            for item in sources_data.get("sources", []) or []
            if isinstance(item, dict) and item.get("source_id")
        }
        source_ids = set(source_by_id)

    integrity_path = case_dir / "investigation-integrity.yml"
    covered_sources: set[str] = set()
    if integrity_path.exists():
        data, err = safe_load_yaml(integrity_path)
        if err:
            errors.append(f"Could not parse investigation-integrity.yml: {err}")
        elif not isinstance(data, dict):
            errors.append("investigation-integrity.yml must contain a YAML object.")
        else:
            file_errors, covered_sources = validate_integrity_file(data, schema, source_ids)
            errors.extend(file_errors)

    claims_by_source = strong_world_claims_using_sources(claims_data, evidence_data)
    for source_id, source in source_by_id.items():
        if source_id not in claims_by_source:
            continue
        risk = source_weight_value(source, "institutional_interest_risk")
        adversarial = source_weight_value(source, "adversarial_relevance")
        if adversarial is None:
            if source.get("source_type") in CLOSURE_SENSITIVE_SOURCE_TYPES:
                claim_list = ", ".join(sorted(claims_by_source[source_id]))
                errors.append(
                    f"source '{source_id}' is closure-sensitive by source_type='{source.get('source_type')}' "
                    f"and is used by strong world claim(s) {claim_list}, but source_weight.adversarial_relevance is missing."
                )
            continue

        numeric_trigger = risk is not None and risk >= RISK_THRESHOLD and adversarial >= ADVERSARIAL_THRESHOLD
        type_trigger = source.get("source_type") in CLOSURE_SENSITIVE_SOURCE_TYPES and adversarial >= ADVERSARIAL_THRESHOLD
        if (numeric_trigger or type_trigger) and source_id not in covered_sources:
            claim_list = ", ".join(sorted(claims_by_source[source_id]))
            if type_trigger:
                errors.append(
                    f"source '{source_id}' is closure-sensitive by source_type='{source.get('source_type')}' "
                    f"and adversarial_relevance={adversarial:.2f}; used by strong world claim(s) {claim_list}, "
                    "so investigation-integrity.yml must cover it."
                )
            else:
                errors.append(
                    f"source '{source_id}' has institutional_interest_risk={risk:.2f} and adversarial_relevance={adversarial:.2f}; "
                    f"used by strong world claim(s) {claim_list}, so investigation-integrity.yml must cover it."
                )

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
        print(f"No case directories found under {root}")
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
        print(f"\n{total_errors} investigation-integrity error(s) found.")
        return 1
    print("\nAll investigation-integrity checks valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
