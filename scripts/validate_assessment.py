#!/usr/bin/env python3
"""Validate assessment lifecycle and redteam gate across all cases."""

import sys
import json
import pathlib
import yaml
import jsonschema

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "assessment.v1.schema.json"
REDTEAM_SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "redteam-review.v1.schema.json"

FINAL_STATUSES = {"final_under_uncertainty", "superseded", "archived"}


def load_schema(path):
    with open(path) as f:
        return json.load(f)


def validate_lifecycle(lifecycle_file: pathlib.Path, schema: dict, redteam_schema: dict) -> int:
    """Validate lifecycle.yml and associated redteam if present. Returns error count."""
    try:
        with open(lifecycle_file) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"FAIL {lifecycle_file}: Could not parse YAML: {e}")
        return 1

    errors = []

    # Build a minimal assessment-like dict for schema validation
    assessment_dict = {
        "schema_version": "1.0",
        "assessment_id": data.get("assessment_id", ""),
        "case_ref": data.get("case_ref", ""),
        "status": data.get("status", ""),
        "lifecycle": {
            "created_at": data.get("created_at", ""),
            "last_reviewed_at": data.get("last_reviewed_at", ""),
            "review_after": data.get("review_after", ""),
        },
        "verdict": {},
        "redteam_ref": data.get("redteam_ref", "redteam.md"),
    }

    # Locate redteam file
    case_dir = lifecycle_file.parent
    redteam_file = case_dir / "redteam.yml"

    # Check redteam gate for final statuses
    status = data.get("status", "")
    if status in FINAL_STATUSES:
        if not redteam_file.exists():
            errors.append(
                f"  Assessment status is '{status}' but no redteam.yml found."
            )
        else:
            try:
                with open(redteam_file) as f:
                    redteam_data = yaml.safe_load(f)
                redteam_verdict = redteam_data.get("verdict", {}).get("status", "")
                if redteam_verdict != "passed" and redteam_verdict != "passed_with_notes":
                    errors.append(
                        f"  Assessment status is '{status}' but redteam verdict is '{redteam_verdict}'. "
                        f"Must be 'passed' or 'passed_with_notes'."
                    )
            except Exception as e:
                errors.append(f"  Could not parse redteam.yml: {e}")

    if errors:
        print(f"FAIL {lifecycle_file}:")
        for e in errors:
            print(e)
        return len(errors)
    else:
        print(f"OK   {lifecycle_file}")
        return 0


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    schema = load_schema(SCHEMA_PATH)
    redteam_schema = load_schema(REDTEAM_SCHEMA_PATH)

    files = sorted(root.rglob("lifecycle.yml"))

    if not files:
        print(f"No lifecycle.yml files found under {root}")
        return 0

    total_errors = 0
    for f in files:
        if "_template" in f.parts:
            continue
        total_errors += validate_lifecycle(f, schema, redteam_schema)

    if total_errors:
        print(f"\n{total_errors} error(s) found.")
        return 1
    else:
        print(f"\nAll assessments valid.")
        return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
