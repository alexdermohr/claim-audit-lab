#!/usr/bin/env python3
"""Validate hypothesis-support-ledger.yml files and their case-local references."""

from collections import Counter
import json
import pathlib
import sys

from jsonschema_compat import jsonschema
import yaml

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "hypothesis-support-ledger.v1.schema.json"
DOWNGRADED_STATUSES = {"weak", "contradicted", "speculative"}


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


def _ids_from_file(path: pathlib.Path, top_key: str, id_key: str) -> set[str]:
    data, err = safe_load_yaml(path)
    if err or not isinstance(data, dict):
        return set()
    return {
        item.get(id_key)
        for item in data.get(top_key, [])
        if isinstance(item, dict) and item.get(id_key)
    }


def validate_case(case_dir: pathlib.Path, schema: dict) -> list[str]:
    errors: list[str] = []
    hypotheses_path = case_dir / "hypotheses.yml"
    ledger_path = case_dir / "hypothesis-support-ledger.yml"
    evidence_path = case_dir / "evidence-pack.yml"
    sources_path = case_dir / "sources.yml"

    if not hypotheses_path.exists():
        if ledger_path.exists():
            return ["hypothesis-support-ledger.yml exists but hypotheses.yml is missing."]
        return errors

    hypotheses_data, err = safe_load_yaml(hypotheses_path)
    if err:
        return [f"Could not parse hypotheses.yml: {err}"]
    if not isinstance(hypotheses_data, dict):
        return ["hypotheses.yml must contain a YAML object."]

    hypotheses = hypotheses_data.get("hypotheses", [])
    if not isinstance(hypotheses, list):
        return ["hypotheses.yml 'hypotheses' must be an array."]

    hypothesis_id_list: list[str] = []
    hypothesis_status: dict[str, str] = {}
    for index, hypothesis in enumerate(hypotheses):
        if not isinstance(hypothesis, dict):
            errors.append(f"hypotheses.yml hypothesis at index {index} must be an object.")
            continue
        hypothesis_id = hypothesis.get("id")
        if not hypothesis_id:
            errors.append(f"hypotheses.yml hypothesis at index {index} is missing required id.")
            continue
        hypothesis_id_list.append(hypothesis_id)
        hypothesis_status[hypothesis_id] = hypothesis.get("status")

    for hypothesis_id, count in sorted(Counter(hypothesis_id_list).items()):
        if count > 1:
            errors.append(f"hypotheses.yml has duplicate hypothesis id '{hypothesis_id}'.")

    hypothesis_ids = set(hypothesis_id_list)

    if not ledger_path.exists():
        return ["hypothesis-support-ledger.yml required because hypotheses.yml exists."]

    ledger_data, err = safe_load_yaml(ledger_path)
    if err:
        return [f"Could not parse hypothesis-support-ledger.yml: {err}"]
    if not isinstance(ledger_data, dict):
        return ["hypothesis-support-ledger.yml must contain a YAML object."]

    errors.extend(schema_errors(ledger_data, schema))
    if errors:
        return errors

    records = ledger_data.get("records", [])
    record_refs = [record.get("hypothesis_ref") for record in records if isinstance(record, dict)]
    record_ref_set = set(record_refs)

    for ref, count in sorted(Counter(record_refs).items()):
        if count > 1:
            errors.append(f"hypothesis-support-ledger.yml has duplicate record for hypothesis_ref '{ref}'.")

    for hypothesis_id in sorted(hypothesis_ids - record_ref_set):
        errors.append(f"hypothesis '{hypothesis_id}' requires exactly one hypothesis-support-ledger record.")

    for hypothesis_ref in sorted(record_ref_set - hypothesis_ids):
        errors.append(f"hypothesis-support-ledger record hypothesis_ref '{hypothesis_ref}' not found in hypotheses.yml.")

    evidence_ids: set[str] = set()
    source_ids: set[str] = set()
    if evidence_path.exists():
        evidence_ids = _ids_from_file(evidence_path, "evidence", "evidence_id")
    if sources_path.exists():
        source_ids = _ids_from_file(sources_path, "sources", "source_id")

    for record in records:
        if not isinstance(record, dict):
            continue
        hypothesis_ref = record.get("hypothesis_ref", "?")
        support_evidence_refs = record.get("supporting_evidence_refs", [])
        support_source_refs = record.get("best_supporting_source_refs", [])

        if support_evidence_refs and not evidence_path.exists():
            errors.append(
                f"hypothesis-support-ledger record '{hypothesis_ref}' references evidence, but evidence-pack.yml is missing."
            )
        for evidence_ref in support_evidence_refs:
            if evidence_path.exists() and evidence_ref not in evidence_ids:
                errors.append(
                    f"hypothesis-support-ledger record '{hypothesis_ref}' evidence_ref '{evidence_ref}' not found in evidence-pack.yml."
                )

        if support_source_refs and not sources_path.exists():
            errors.append(
                f"hypothesis-support-ledger record '{hypothesis_ref}' references sources, but sources.yml is missing."
            )
        for source_ref in support_source_refs:
            if sources_path.exists() and source_ref not in source_ids:
                errors.append(
                    f"hypothesis-support-ledger record '{hypothesis_ref}' source_ref '{source_ref}' not found in sources.yml."
                )

        if not support_evidence_refs and not record.get("not_found"):
            errors.append(
                f"hypothesis-support-ledger record '{hypothesis_ref}' with empty supporting_evidence_refs must include at least one not_found entry."
            )

        status = hypothesis_status.get(hypothesis_ref)
        if status in DOWNGRADED_STATUSES:
            search_status = record.get("support_search_status")
            if search_status not in {"completed", "blocked"}:
                errors.append(
                    f"hypothesis '{hypothesis_ref}' status='{status}' requires support_search_status completed or blocked."
                )
            if search_status == "blocked" and not record.get("not_found"):
                errors.append(
                    f"hypothesis '{hypothesis_ref}' support search is blocked but lacks an explicit not_found or blocked explanation."
                )
            if (
                search_status == "completed"
                and record.get("missing_for_upgrade")
                and not record.get("not_found")
            ):
                errors.append(
                    f"hypothesis '{hypothesis_ref}' status='{status}' has missing_for_upgrade entries and completed support search, so not_found must document the unresolved support gaps."
                )
            for field in ("strongest_supporting_argument", "steelman"):
                if not record.get(field, "").strip():
                    errors.append(
                        f"hypothesis '{hypothesis_ref}' status='{status}' requires non-empty {field}."
                    )
            for field in ("missing_for_upgrade", "searched_for"):
                if not record.get(field):
                    errors.append(
                        f"hypothesis '{hypothesis_ref}' status='{status}' requires at least one {field} entry."
                    )

    return errors


def is_case_dir(path: pathlib.Path) -> bool:
    # Transitional rollout: only opted-in cases are scanned by the CLI.
    # validate_case() remains strict for direct tests and future hardening.
    return (path / "hypothesis-support-ledger.yml").exists()


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    schema = load_schema()

    # Transitional rollout: discover only case directories that opted in with
    # hypothesis-support-ledger.yml; future hardening may scan hypotheses.yml.
    candidate_dirs = {root}
    candidate_dirs.update(marker.parent for marker in root.rglob("hypothesis-support-ledger.yml"))
    case_dirs = sorted(
        d for d in candidate_dirs
        if d.is_dir() and "_template" not in d.parts and is_case_dir(d)
    )

    if not case_dirs:
        print(f"No hypothesis-support case directories found under {root}")
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
        print(f"\n{total_errors} hypothesis-support ledger error(s) found.")
        return 1

    print("\nAll hypothesis-support ledgers valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
