#!/usr/bin/env python3
"""Validate that claims using absence language are typed as absence_claim
with bounded scope, forbidden-upgrade declaration, and closure caps."""

from __future__ import annotations

import pathlib
import re
import sys

import yaml

# Trigger phrases that indicate absence language
ABSENCE_TRIGGERS = [
    # German
    "nicht nachgewiesen",
    "keine evidenz",
    "kein nachweis",
    "nicht belegt",
    "keine belege",
    "keine hinweise",
    # English
    "no evidence",
    "no proof",
    "not found",
    "not documented",
    "absence of evidence",
    "no indication",
]

STRONG_STATUSES = {"established", "strongly_supported"}

EXHAUSTIVITY_MARKERS = [
    "exhaustive search",
    "exhaustiv geprüft",
    "vollständig geprüft",
    "vollständige suche",
]

CASE_MARKERS = (
    "claims.yml",
    "evidence-relations.yml",
    "anomaly-ledger.yml",
    "investigation-integrity.yml",
)


def _has_trigger(text: str) -> bool:
    lower = text.lower()
    return any(t in lower for t in ABSENCE_TRIGGERS)


def _has_exhaustivity_marker(scope: str) -> bool:
    lower = scope.lower()
    return any(m in lower for m in EXHAUSTIVITY_MARKERS)


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


def validate_case(case_dir: pathlib.Path) -> list[str]:
    claims_file = case_dir / "claims.yml"
    if not claims_file.exists():
        return []

    try:
        with open(claims_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        return [f"FAIL {claims_file}: Could not parse YAML: {e}"]

    if not isinstance(data, dict):
        return []

    claims = data.get("claims", [])
    if not isinstance(claims, list):
        return []

    errors: list[str] = []

    for claim in claims:
        if not isinstance(claim, dict):
            continue

        claim_id = claim.get("claim_id", "<unknown>")
        statement = claim.get("statement", "")
        notes = claim.get("notes", "")

        # Determine if absence language is present
        trigger_text = f"{statement} {notes}"
        trigger_found = None
        for t in ABSENCE_TRIGGERS:
            if t in trigger_text.lower():
                trigger_found = t
                break

        if trigger_found is None:
            continue

        kind = claim.get("claim_kind")
        absence_scope = claim.get("absence_scope")
        forbidden_upgrades = claim.get("forbidden_upgrades") or []
        status = claim.get("status", "")
        evidence_refs = claim.get("evidence_refs") or []

        # A) Typing: claim_kind must be absence_claim
        if kind != "absence_claim":
            errors.append(
                f"FAIL {claims_file}: claim {claim_id} field claim_kind: "
                f"trigger '{trigger_found}' requires claim_kind: absence_claim "
                f"(found: {kind!r}). Set claim_kind: absence_claim."
            )
            continue  # skip further checks; primary violation first

        # B) Scope: absence_scope must exist and be non-empty string
        if not isinstance(absence_scope, str) or not absence_scope.strip():
            errors.append(
                f"FAIL {claims_file}: claim {claim_id} field absence_scope: "
                f"absence_claim requires a non-empty absence_scope string. "
                f"Add absence_scope: describing the bounded search space."
            )

        # C) Forbidden upgrade declaration
        if "absence_of_evidence_to_falsehood" not in forbidden_upgrades:
            errors.append(
                f"FAIL {claims_file}: claim {claim_id} field forbidden_upgrades: "
                f"absence_claim must include absence_of_evidence_to_falsehood. "
                f"Add it to forbidden_upgrades."
            )

        # D) Closure cap: strong statuses require exhaustivity marker + evidence_refs
        if status in STRONG_STATUSES:
            scope_str = absence_scope if isinstance(absence_scope, str) else ""
            has_exhaustivity = _has_exhaustivity_marker(scope_str)
            has_evidence = bool(evidence_refs)

            if not has_exhaustivity or not has_evidence:
                missing = []
                if not has_exhaustivity:
                    missing.append(
                        "absence_scope containing an exhaustivity marker "
                        "(e.g. 'exhaustive search', 'vollständig geprüft')"
                    )
                if not has_evidence:
                    missing.append("non-empty evidence_refs")
                errors.append(
                    f"FAIL {claims_file}: claim {claim_id} field status: "
                    f"status '{status}' on absence_claim without "
                    f"{' and '.join(missing)}. "
                    f"Use weak/plausible/unresolved/no_verdict_possible/speculative, "
                    f"or add exhaustivity marker and evidence_refs."
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
    print("\nAll absence-language scope checks valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
