#!/usr/bin/env python3
"""Validate source-weight-audit.yml coverage for sources with source_weight."""

import json
from collections import Counter
import pathlib
import sys

from jsonschema_compat import jsonschema
import yaml

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "source-weight-audit.v1.schema.json"


def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def safe_load_yaml(path: pathlib.Path):
    """Return (data, error_string). data is None on failure."""
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except Exception as exc:
        return None, str(exc)


def schema_errors(payload: dict, schema: dict) -> list[str]:
    validator = jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())
    return [
        f"Schema error at {list(error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda err: list(err.absolute_path))
    ]


def validate_case(case_dir: pathlib.Path, schema: dict) -> list[str]:
    errors: list[str] = []
    sources_path = case_dir / "sources.yml"
    audit_path = case_dir / "source-weight-audit.yml"
    evidence_path = case_dir / "evidence-pack.yml"

    if not sources_path.exists():
        if audit_path.exists():
            return ["source-weight-audit.yml exists but sources.yml is missing."]
        return errors

    sources_data, err = safe_load_yaml(sources_path)
    if err:
        return [f"Could not parse sources.yml: {err}"]
    if not isinstance(sources_data, dict):
        return ["sources.yml must contain a YAML object."]

    sources = sources_data.get("sources", [])
    source_ids = {s.get("source_id") for s in sources if isinstance(s, dict) and s.get("source_id")}
    weighted_source_ids = {
        s.get("source_id")
        for s in sources
        if isinstance(s, dict) and s.get("source_id") and "source_weight" in s
    }

    if not weighted_source_ids:
        return errors

    if not audit_path.exists():
        return [
            "source-weight-audit.yml required because sources.yml assigns source_weight values."
        ]

    audit_data, err = safe_load_yaml(audit_path)
    if err:
        return [f"Could not parse source-weight-audit.yml: {err}"]
    if not isinstance(audit_data, dict):
        return ["source-weight-audit.yml must contain a YAML object."]

    errors.extend(schema_errors(audit_data, schema))
    if errors:
        return errors

    records = audit_data.get("records", [])
    record_refs = [record.get("source_ref") for record in records if isinstance(record, dict)]
    record_ref_set = set(record_refs)

    ref_counts = Counter(record_refs)
    for ref, count in sorted(ref_counts.items()):
        if count <= 1:
            continue
        errors.append(f"source-weight-audit.yml has duplicate record for source_ref '{ref}'.")

    for source_id in sorted(weighted_source_ids - record_ref_set):
        errors.append(f"source_weight for '{source_id}' requires a source-weight-audit record.")

    for source_ref in sorted(record_ref_set - source_ids):
        errors.append(f"source-weight-audit record source_ref '{source_ref}' not found in sources.yml.")

    evidence_ids: set[str] = set()
    evidence_source_by_id: dict[str, str] = {}
    evidence_data = None

    if not evidence_path.exists():
        errors.append(
            "evidence-pack.yml required because source-weight audits for weighted sources require same-source evidence references."
        )

    if evidence_path.exists():
        evidence_data, err = safe_load_yaml(evidence_path)
        if err:
            errors.append(f"Could not parse evidence-pack.yml: {err}")
            evidence_data = None
        elif not isinstance(evidence_data, dict):
            errors.append("evidence-pack.yml must contain a YAML object.")
            evidence_data = None
        else:
            evidence_ids = {
                ev.get("evidence_id")
                for ev in evidence_data.get("evidence", [])
                if isinstance(ev, dict) and ev.get("evidence_id")
            }
            evidence_source_by_id = {
                ev.get("evidence_id"): ev.get("source_ref")
                for ev in evidence_data.get("evidence", [])
                if isinstance(ev, dict) and ev.get("evidence_id")
            }

    any_evidence_refs = False
    for record in records:
        if not isinstance(record, dict):
            continue
        source_ref = record.get("source_ref", "?")
        record_evidence_refs = record.get("evidence_refs", [])
        has_same_source_evidence = False
        if source_ref in weighted_source_ids and not record_evidence_refs:
            errors.append(
                f"source-weight-audit record '{source_ref}' must reference at least one evidence item."
            )
        for evidence_ref in record_evidence_refs:
            any_evidence_refs = True
            if evidence_data is not None and evidence_ref not in evidence_ids:
                errors.append(
                    f"source-weight-audit record '{source_ref}' evidence_ref '{evidence_ref}' not found in evidence-pack.yml."
                )
            if evidence_source_by_id.get(evidence_ref) == source_ref:
                has_same_source_evidence = True

        if source_ref in weighted_source_ids and evidence_data is not None and record_evidence_refs and not has_same_source_evidence:
            errors.append(
                f"source-weight-audit record '{source_ref}' must reference at least one evidence item from the same source."
            )

    if any_evidence_refs and not evidence_path.exists():
        errors.append(
            "evidence-pack.yml required because source-weight-audit.yml references evidence IDs, but file is missing."
        )

    return errors


def is_case_dir(path: pathlib.Path) -> bool:
    return (path / "sources.yml").exists() or (path / "source-weight-audit.yml").exists()


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    schema = load_schema()

    candidate_dirs = {root}
    for marker_name in ("sources.yml", "source-weight-audit.yml"):
        candidate_dirs.update(marker.parent for marker in root.rglob(marker_name))
    case_dirs = sorted(
        d for d in candidate_dirs
        if d.is_dir() and "_template" not in d.parts and is_case_dir(d)
    )

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
        print(f"\n{total_errors} source-weight audit error(s) found.")
        return 1

    print("\nAll source-weight audits valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
