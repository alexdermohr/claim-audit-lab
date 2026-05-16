#!/usr/bin/env python3
"""Validate that mechanical migration relations do not masquerade as strong semantic evidence."""

import pathlib
import sys
import yaml

MECHANICAL_MARKER = "not a semantic upgrade"
FORBIDDEN_MECHANICAL_TYPES = {"supports_directly", "contradicts_directly"}
MAX_MECHANICAL_STRENGTH = 0.6


def safe_load_yaml(path: pathlib.Path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except Exception as exc:
        return None, str(exc)


def validate_file(path: pathlib.Path) -> list[str]:
    data, err = safe_load_yaml(path)
    if err:
        return [f"Could not parse {path}: {err}"]
    if not isinstance(data, dict):
        return []

    errors: list[str] = []
    for relation in data.get("relations", []) or []:
        if not isinstance(relation, dict):
            continue
        explanation = relation.get("explanation", "")
        if not isinstance(explanation, str):
            explanation = ""
        if MECHANICAL_MARKER not in explanation.lower():
            continue
        relation_id = relation.get("relation_id", "?")
        relation_type = relation.get("relation_type")
        strength = relation.get("strength")
        if relation_type in FORBIDDEN_MECHANICAL_TYPES:
            errors.append(
                f"FAIL {path}: mechanical migration relation '{relation_id}' must not use relation_type='{relation_type}'."
            )
        if isinstance(strength, (int, float)) and strength > MAX_MECHANICAL_STRENGTH:
            errors.append(
                f"FAIL {path}: mechanical migration relation '{relation_id}' strength must be <= {MAX_MECHANICAL_STRENGTH}."
            )
    return errors


def validate(root: pathlib.Path) -> list[str]:
    if root.is_file():
        return validate_file(root)
    errors: list[str] = []
    for path in sorted(root.rglob("evidence-relations.yml")):
        if "_template" in path.parts:
            continue
        errors.extend(validate_file(path))
    return errors


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    errors = validate(root)
    if errors:
        for error in errors:
            print(error)
        print(f"\n{len(errors)} mechanical-migration discipline error(s) found.")
        return 1
    print(f"All mechanical migration relations valid under {root}.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
