#!/usr/bin/env python3
"""Validate evidence-pack.yml files in all cases against evidence-pack.v1.schema.json."""

import sys
import json
import pathlib
import yaml
from jsonschema_compat import jsonschema

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "evidence-pack.v1.schema.json"


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def validate_file(pack_file: pathlib.Path, schema: dict) -> int:
    try:
        with open(pack_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"FAIL {pack_file}: Could not parse YAML: {e}")
        return 1

    validator = jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())
    errors = list(validator.iter_errors(data))

    if errors:
        print(f"FAIL {pack_file}:")
        for error in errors:
            print(f"  Schema error at {list(error.absolute_path)}: {error.message}")
        return len(errors)

    print(f"OK   {pack_file}")
    return 0


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    schema = load_schema()

    files = sorted(root.rglob("evidence-pack.yml"))

    if not files:
        print(f"No evidence-pack.yml files found under {root}")
        return 0

    total_errors = 0
    for f in files:
        if "_template" in f.parts:
            continue
        total_errors += validate_file(f, schema)

    if total_errors:
        print(f"\n{total_errors} error(s) found.")
        return 1

    print("\nAll evidence packs valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
