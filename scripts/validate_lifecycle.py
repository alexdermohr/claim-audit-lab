#!/usr/bin/env python3
"""Validate lifecycle.yml and linked redteam artifacts across all cases."""

import json
import pathlib
import sys

import jsonschema
import yaml

LIFECYCLE_SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "lifecycle.v1.schema.json"
REDTEAM_SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "redteam-review.v1.schema.json"

FINAL_STATUSES = {"final_under_uncertainty"}
REDTEAM_PASSING_VERDICTS = {"passed", "passed_with_notes"}


def load_schema(path: pathlib.Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def schema_errors(payload: dict, schema: dict) -> list[str]:
    validator = jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())
    return [
        f"Schema error at {list(error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda err: list(err.absolute_path))
    ]


def validate_lifecycle_file(
    lifecycle_file: pathlib.Path,
    lifecycle_schema: dict,
    redteam_schema: dict,
) -> list[str]:
    errors: list[str] = []

    try:
        with open(lifecycle_file, encoding="utf-8") as f:
            lifecycle_data = yaml.safe_load(f)
    except Exception as exc:  # pragma: no cover - defensive I/O branch
        return [f"Could not parse YAML: {exc}"]

    if not isinstance(lifecycle_data, dict):
        return ["Lifecycle file must contain a YAML object."]

    errors.extend(schema_errors(lifecycle_data, lifecycle_schema))
    if errors:
        return errors

    case_dir = lifecycle_file.parent
    redteam_ref = lifecycle_data["redteam_ref"]
    redteam_file = case_dir / redteam_ref

    if not redteam_file.exists():
        if lifecycle_data["status"] in FINAL_STATUSES:
            errors.append(
                f"Status '{lifecycle_data['status']}' requires a red-team file but '{redteam_ref}' does not exist."
            )
        return errors

    try:
        with open(redteam_file, encoding="utf-8") as f:
            redteam_data = yaml.safe_load(f)
    except Exception as exc:  # pragma: no cover - defensive I/O branch
        return [f"Could not parse red-team YAML '{redteam_ref}': {exc}"]

    if not isinstance(redteam_data, dict):
        return [f"Red-team file '{redteam_ref}' must contain a YAML object."]

    redteam_schema_errs = schema_errors(redteam_data, redteam_schema)
    errors.extend([f"{redteam_ref}: {err}" for err in redteam_schema_errs])
    if errors:
        return errors

    status = lifecycle_data["status"]
    redteam_verdict = redteam_data.get("verdict", {}).get("status", "")

    if status in FINAL_STATUSES and redteam_verdict not in REDTEAM_PASSING_VERDICTS:
        errors.append(
            f"Status '{status}' requires red-team verdict in {sorted(REDTEAM_PASSING_VERDICTS)}, got '{redteam_verdict}'."
        )

    if redteam_verdict == "blocked" and status == "final_under_uncertainty":
        errors.append("Red-team verdict 'blocked' is incompatible with lifecycle status 'final_under_uncertainty'.")

    return errors


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    lifecycle_schema = load_schema(LIFECYCLE_SCHEMA_PATH)
    redteam_schema = load_schema(REDTEAM_SCHEMA_PATH)

    files = sorted(root.rglob("lifecycle.yml"))
    if not files:
        print(f"No lifecycle.yml files found under {root}")
        return 0

    total_errors = 0
    for lifecycle_file in files:
        if "_template" in lifecycle_file.parts:
            continue

        errors = validate_lifecycle_file(lifecycle_file, lifecycle_schema, redteam_schema)
        if errors:
            print(f"FAIL {lifecycle_file}:")
            for err in errors:
                print(f"  {err}")
            total_errors += len(errors)
        else:
            print(f"OK   {lifecycle_file}")

    if total_errors:
        print(f"\n{total_errors} error(s) found.")
        return 1

    print("\nAll lifecycles valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
