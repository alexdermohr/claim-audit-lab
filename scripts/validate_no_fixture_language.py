#!/usr/bin/env python3
"""Reject test/fixture language in production case files."""

import pathlib
import re
import sys

FORBIDDEN_TERMS = ("fixture", "synthetic", "placeholder", "migration-fixture")
FORBIDDEN_RE = re.compile("|".join(re.escape(term) for term in FORBIDDEN_TERMS), re.IGNORECASE)
ALLOWED_PARTS = {"sandbox", "_template"}


def is_allowed_case_path(path: pathlib.Path) -> bool:
    parts = path.parts
    try:
        cases_index = parts.index("cases")
    except ValueError:
        return False
    if cases_index + 1 >= len(parts):
        return False
    return parts[cases_index + 1] in ALLOWED_PARTS


def scan_file(path: pathlib.Path) -> list[str]:
    if is_allowed_case_path(path):
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    matches = []
    seen = set()
    for match in FORBIDDEN_RE.finditer(text):
        term = match.group(0)
        key = term.lower()
        if key not in seen:
            seen.add(key)
            matches.append(f"FAIL {path}: forbidden fixture/test language in production case: {term}")
    return matches


def validate(root: pathlib.Path) -> list[str]:
    if root.is_file():
        return scan_file(root)
    errors: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            errors.extend(scan_file(path))
    return errors


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    errors = validate(root)
    if errors:
        for error in errors:
            print(error)
        print(f"\n{len(errors)} fixture-language error(s) found.")
        return 1
    print(f"No forbidden fixture/test language found under {root}.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
