#!/usr/bin/env python3
"""Validate that evidence records cite only their declared source_ref.

An evidence record whose source_ref is s005 must not explicitly cite s001
via a citation marker. Cross-source reasoning belongs in evidence-relations.yml,
inference-ledger.yml, or assessment.md.
"""

from __future__ import annotations

import pathlib
import re
import sys

import yaml

# Citation marker patterns: each group captures a source ID.
# Pattern: marker text followed by a source ID (s followed by 3+ digits).
_CITATION_PATTERN = re.compile(
    r"(?:"
    r"source\s+position\s+from\s+"
    r"|quoted?\s+from\s+"
    r"|(?<!\w)from\s+"
    r"|siehe\s+"
    r"|quelle:\s*"
    r"|(?<!\w)source\s+"
    r")"
    r"(s[0-9]{3,})",
    re.IGNORECASE,
)

EVIDENCE_TEXT_FIELDS = [
    "summary",
    "verbatim_or_ref",
    "evidence_excerpt",
    "locator",
    "notes",
]

CASE_MARKERS = (
    "claims.yml",
    "evidence-relations.yml",
    "anomaly-ledger.yml",
    "investigation-integrity.yml",
)


def is_case_dir(path: pathlib.Path) -> bool:
    return any((path / marker).exists() for marker in CASE_MARKERS)


def discover_case_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    candidate_dirs = {root}
    for marker in CASE_MARKERS:
        candidate_dirs.update(path.parent for path in root.rglob(marker))
    return sorted(
        d
        for d in candidate_dirs
        if d.is_dir() and "_template" not in d.parts and is_case_dir(d)
    )


def _cited_source_ids(ev: dict) -> set[str]:
    """Return all source IDs cited via explicit citation markers."""
    text = " ".join(str(ev.get(f, "")) for f in EVIDENCE_TEXT_FIELDS)
    return set(_CITATION_PATTERN.findall(text.lower()))


def validate_case(case_dir: pathlib.Path) -> list[str]:
    pack_file = case_dir / "evidence-pack.yml"
    if not pack_file.exists():
        return []

    try:
        with open(pack_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        return [f"FAIL {pack_file}: Could not parse YAML: {e}"]

    if not isinstance(data, dict):
        return []

    evidence_list = data.get("evidence", [])
    if not isinstance(evidence_list, list):
        return []

    errors: list[str] = []

    for ev in evidence_list:
        if not isinstance(ev, dict):
            continue

        eid = ev.get("evidence_id", ev.get("id", "<unknown>"))
        source_ref = ev.get("source_ref", "")
        if not isinstance(source_ref, str):
            source_ref = str(source_ref)
        source_ref_lower = source_ref.strip().lower()

        cited = _cited_source_ids(ev)

        if not cited:
            # No explicit citation markers found — pass
            continue

        if len(cited) > 1:
            errors.append(
                f"FAIL {pack_file}: evidence {eid}: "
                f"multiple source IDs cited via markers: {sorted(cited)}. "
                f"Evidence must be atomic; split cross-source evidence into "
                f"separate records. Cross-source reasoning belongs in "
                f"evidence-relations.yml, inference-ledger.yml, or assessment.md."
            )
        elif cited != {source_ref_lower}:
            cited_id = next(iter(cited))
            errors.append(
                f"FAIL {pack_file}: evidence {eid} field citation marker: "
                f"cites source {cited_id!r} via explicit marker but "
                f"source_ref is {source_ref!r}. "
                f"Change source_ref to match the cited source, or remove the "
                f"mismatched citation marker."
            )

    return errors


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    case_dirs = discover_case_dirs(root)

    if not case_dirs:
        print(f"No case directories found under {root}")
        return 0

    total_errors: list[str] = []
    for case_dir in case_dirs:
        errs = validate_case(case_dir)
        total_errors.extend(errs)

    if total_errors:
        for err in total_errors:
            print(err)
        print(f"\n{len(total_errors)} error(s) found.")
        return 1

    for case_dir in case_dirs:
        print(f"OK   {case_dir}")
    print("\nAll evidence-source alignment checks valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
