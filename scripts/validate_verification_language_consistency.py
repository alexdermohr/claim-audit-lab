#!/usr/bin/env python3
"""Validate that background-only and unverified artefacts do not use
positive verification language in their content fields.

Two gates:

A) Background-only language gate
   If answer-receipt.yml has external_research.background_knowledge_only: true,
   specific content fields must not assert positive verification language.
   what_would_change_assessment is exempt (hypothetical phrasing allowed there).

B) Claim-vs-Source-Verification Gate
   If all sources referenced by a claim have source_verification.status: unverified,
   the claim's statement and notes must not contain positive verification language.
"""

from __future__ import annotations

import pathlib
import re
import sys

import yaml

# Positive verification patterns (case-insensitive, literal sub-string match)
POSITIVE_VERIFICATION_PATTERNS = [
    "verifizierte quellen",
    "in verifizierten quellen",
    "extern verifiziert",
    "externally verified",
    "verified sources",
    "in verified sources",
    "verified evidence",
    "extern geprüft",
    "geprüfte quellen",
    "validierte quellen",
]

# Negation / discipline patterns that neutralise a positive match.
# If a line contains a positive pattern AND a negation pattern, it is allowed.
NEGATION_PATTERNS = [
    "nicht extern verifiziert",
    "nicht verifiziert",
    "unverified",
    "als unverified markiert",
    "background-knowledge-only",
    "no external verification",
    "keine externe verifikation",
    "im vorliegenden quellenpaket nicht belegt",
    "im als unverified markierten quellenpaket nicht belegt",
]

# Fields checked under the background-only gate (receipt + other files)
RECEIPT_FIELDS_TO_CHECK = ["answer_summary", "final_uncertainty_statement", "notes"]
CLAIM_FIELDS_TO_CHECK = ["statement", "notes"]
EVIDENCE_FIELDS_TO_CHECK = [
    "summary",
    "notes",
    "verbatim_or_ref",
    "evidence_excerpt",
    "locator",
]

# what_would_change_assessment is explicitly exempted
EXEMPT_RECEIPT_FIELDS = {"what_would_change_assessment"}

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


def _iter_units(text: str) -> list[str]:
    """Split text into sentence/line-sized units for local negation handling."""
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p for p in parts if p.strip()]


def _has_positive_pattern(text: str) -> str | None:
    """Return the first matched positive verification pattern, or None."""
    for unit in _iter_units(text):
        lower = unit.lower()
        for pat in POSITIVE_VERIFICATION_PATTERNS:
            if pat in lower:
                # Negation only neutralises within the same sentence/line unit.
                if any(neg in lower for neg in NEGATION_PATTERNS):
                    continue
                return pat
    return None


def _load_yaml(path: pathlib.Path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except Exception as exc:
        return None, str(exc)


def validate_case(case_dir: pathlib.Path) -> list[str]:
    errors: list[str] = []

    # --- Load answer-receipt ---
    receipt_file = case_dir / "answer-receipt.yml"
    background_only = False

    if receipt_file.exists():
        receipt, err = _load_yaml(receipt_file)
        if err:
            return [f"FAIL {receipt_file}: Could not parse YAML: {err}"]
        if isinstance(receipt, dict):
            ext = receipt.get("external_research") or {}
            background_only = bool(ext.get("background_knowledge_only", False))

    # --- Gate A: Background-only language gate ---
    if background_only:
        # Check receipt fields
        if receipt_file.exists():
            receipt_data, _ = _load_yaml(receipt_file)
            if isinstance(receipt_data, dict):
                for field in RECEIPT_FIELDS_TO_CHECK:
                    val = receipt_data.get(field)
                    if not isinstance(val, str):
                        continue
                    match = _has_positive_pattern(val)
                    if match:
                        errors.append(
                            f"FAIL {receipt_file}: field {field}: "
                            f"background_knowledge_only case uses positive "
                            f"verification language '{match}'. "
                            f"Replace with disciplined absence language, e.g. "
                            f"'im vorliegenden, als unverified markierten "
                            f"Quellenpaket nicht belegt'."
                        )

        # Check claims
        claims_file = case_dir / "claims.yml"
        if claims_file.exists():
            claims_data, err = _load_yaml(claims_file)
            if err:
                errors.append(f"FAIL {claims_file}: Could not parse YAML: {err}")
            elif isinstance(claims_data, dict):
                for claim in claims_data.get("claims", []):
                    if not isinstance(claim, dict):
                        continue
                    cid = claim.get("claim_id", "<unknown>")
                    for field in CLAIM_FIELDS_TO_CHECK:
                        val = claim.get(field)
                        if not isinstance(val, str):
                            continue
                        match = _has_positive_pattern(val)
                        if match:
                            errors.append(
                                f"FAIL {claims_file}: claim {cid} field {field}: "
                                f"background_knowledge_only case uses positive "
                                f"verification language '{match}'. "
                                f"Replace with disciplined absence language."
                            )

        # Check evidence-pack
        pack_file = case_dir / "evidence-pack.yml"
        if pack_file.exists():
            pack_data, err = _load_yaml(pack_file)
            if err:
                errors.append(f"FAIL {pack_file}: Could not parse YAML: {err}")
            elif isinstance(pack_data, dict):
                for ev in pack_data.get("evidence", []):
                    if not isinstance(ev, dict):
                        continue
                    eid = ev.get("evidence_id", ev.get("id", "<unknown>"))
                    for field in EVIDENCE_FIELDS_TO_CHECK:
                        val = ev.get(field)
                        if not isinstance(val, str):
                            continue
                        match = _has_positive_pattern(val)
                        if match:
                            errors.append(
                                f"FAIL {pack_file}: evidence {eid} field {field}: "
                                f"background_knowledge_only case uses positive "
                                f"verification language '{match}'. "
                                f"Replace with disciplined absence language."
                            )

        # Check assessment.md
        assessment_file = case_dir / "assessment.md"
        if assessment_file.exists():
            try:
                text = assessment_file.read_text(encoding="utf-8")
            except Exception as e:
                errors.append(f"FAIL {assessment_file}: Could not read: {e}")
            else:
                match = _has_positive_pattern(text)
                if match:
                    errors.append(
                        f"FAIL {assessment_file}: "
                        f"background_knowledge_only case uses positive "
                        f"verification language '{match}'. "
                        f"Replace with disciplined absence language."
                    )

    # --- Gate B: Claim-vs-Source-Verification Gate ---
    sources_file = case_dir / "sources.yml"
    sources_data = None
    if sources_file.exists():
        sources_data, _ = _load_yaml(sources_file)

    if isinstance(sources_data, dict):
        sources_by_id: dict[str, dict] = {}
        for src in sources_data.get("sources", []):
            if isinstance(src, dict) and src.get("source_id"):
                sources_by_id[src["source_id"]] = src

        claims_file = case_dir / "claims.yml"
        if claims_file.exists():
            claims_data, err = _load_yaml(claims_file)
            if err:
                errors.append(f"FAIL {claims_file}: Could not parse YAML: {err}")
            elif isinstance(claims_data, dict):
                for claim in claims_data.get("claims", []):
                    if not isinstance(claim, dict):
                        continue
                    cid = claim.get("claim_id", "<unknown>")
                    source_refs = claim.get("source_refs") or []
                    if not isinstance(source_refs, list) or not source_refs:
                        continue

                    # Determine aggregate verification status
                    verified_sources = []
                    for ref in source_refs:
                        src = sources_by_id.get(ref)
                        if isinstance(src, dict):
                            sv = src.get("source_verification") or {}
                            vs = sv.get("status", "unverified")
                            verified_sources.append(vs)

                    if not verified_sources:
                        continue

                    all_unverified = all(v == "unverified" for v in verified_sources)

                    if all_unverified:
                        for field in CLAIM_FIELDS_TO_CHECK:
                            val = claim.get(field)
                            if not isinstance(val, str):
                                continue
                            match = _has_positive_pattern(val)
                            if match:
                                errors.append(
                                    f"FAIL {claims_file}: claim {cid} field {field}: "
                                    f"all source_refs are unverified but field uses "
                                    f"positive verification language '{match}'. "
                                    f"Replace with disciplined absence language or "
                                    f"obtain verified sources."
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
    print("\nAll verification-language consistency checks valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
