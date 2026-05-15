#!/usr/bin/env python3
"""Validate sources.yml files in all cases against source.v1.schema.json."""

import sys
import json
import pathlib
import yaml
from jsonschema_compat import jsonschema

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "source.v1.schema.json"


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def validate_source(source: dict, schema: dict) -> list[str]:
    errors = []
    validator = jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())
    for error in validator.iter_errors(source):
        errors.append(f"  Schema error at {list(error.absolute_path)}: {error.message}")
    return errors


def validate_file(sources_file: pathlib.Path, schema: dict) -> int:
    try:
        with open(sources_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"FAIL {sources_file}: Could not parse YAML: {e}")
        return 1

    if not isinstance(data, dict) or "sources" not in data:
        print(f"FAIL {sources_file}: Missing top-level 'sources' key.")
        return 1

    total_errors = 0
    for source in data["sources"]:
        errs = validate_source(source, schema)
        if errs:
            print(f"FAIL {sources_file} [{source.get('source_id', '?')}]:")
            for e in errs:
                print(e)
            total_errors += len(errs)

    if total_errors == 0:
        print(f"OK   {sources_file}")

    return total_errors


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    schema = load_schema()

    files = sorted(root.rglob("sources.yml"))

    if not files:
        print(f"No sources.yml files found under {root}")
        return 0

    total_errors = 0
    for f in files:
        if "_template" in f.parts:
            continue
        total_errors += validate_file(f, schema)

    if total_errors:
        print(f"\n{total_errors} error(s) found.")
        return 1

    print("\nAll sources valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
