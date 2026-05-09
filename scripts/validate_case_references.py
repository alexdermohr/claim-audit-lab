#!/usr/bin/env python3
"""Validate case-local cross-references: sources, evidence, claims, lifecycle, redteam."""

import sys
import pathlib
import yaml

STRONG_STATUSES = {"established", "strongly_supported"}
WEAK_STATUSES = {"weak", "plausible", "speculative", "unresolved", "contradicted", "no_verdict_possible"}

CASE_FILES = {"claims.yml", "sources.yml", "evidence-pack.yml", "lifecycle.yml", "redteam.yml"}


def load_yaml(path: pathlib.Path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_case(case_dir: pathlib.Path) -> list[str]:
    errors = []

    claims_path = case_dir / "claims.yml"
    sources_path = case_dir / "sources.yml"
    evidence_path = case_dir / "evidence-pack.yml"
    lifecycle_path = case_dir / "lifecycle.yml"
    redteam_path = case_dir / "redteam.yml"

    claims_data = load_yaml(claims_path) if claims_path.exists() else None
    sources_data = load_yaml(sources_path) if sources_path.exists() else None
    evidence_data = load_yaml(evidence_path) if evidence_path.exists() else None
    lifecycle_data = load_yaml(lifecycle_path) if lifecycle_path.exists() else None
    redteam_data = load_yaml(redteam_path) if redteam_path.exists() else None

    claims = claims_data.get("claims", []) if claims_data else []
    sources = sources_data.get("sources", []) if sources_data else []
    evidence_items = evidence_data.get("evidence", []) if evidence_data else []

    claim_ids = {c["claim_id"] for c in claims if "claim_id" in c}
    source_ids = {s["source_id"] for s in sources if "source_id" in s}
    evidence_ids = {e["evidence_id"] for e in evidence_items if "evidence_id" in e}

    # Determine which refs are needed
    all_claim_source_refs = set()
    all_claim_evidence_refs = set()
    for claim in claims:
        cid = claim.get("claim_id", "?")
        src_refs = claim.get("source_refs", []) or []
        ev_refs = claim.get("evidence_refs", []) or []
        all_claim_source_refs.update(src_refs)
        all_claim_evidence_refs.update(ev_refs)

        status = claim.get("status", "")

        # Strong claims must have refs
        if status in STRONG_STATUSES:
            if not src_refs:
                errors.append(f"  Claim '{cid}' status='{status}' requires non-empty source_refs.")
            if not ev_refs:
                errors.append(f"  Claim '{cid}' status='{status}' requires non-empty evidence_refs.")

        # All provided source_refs must resolve
        for ref in src_refs:
            if ref not in source_ids:
                errors.append(f"  Claim '{cid}' source_ref '{ref}' not found in sources.yml.")

        # All provided evidence_refs must resolve
        for ref in ev_refs:
            if ref not in evidence_ids:
                errors.append(f"  Claim '{cid}' evidence_ref '{ref}' not found in evidence-pack.yml.")

    # Require sources.yml if any claim references sources
    if all_claim_source_refs and not sources_data:
        errors.append("  sources.yml required because claims reference source IDs, but file is missing.")

    # Require evidence-pack.yml if any claim references evidence
    if all_claim_evidence_refs and not evidence_data:
        errors.append("  evidence-pack.yml required because claims reference evidence IDs, but file is missing.")

    # Validate evidence items
    for ev in evidence_items:
        eid = ev.get("evidence_id", "?")

        src_ref = ev.get("source_ref", "")
        if src_ref and src_ref not in source_ids:
            errors.append(f"  Evidence '{eid}' source_ref '{src_ref}' not found in sources.yml.")
        elif src_ref and not sources_data:
            errors.append(f"  Evidence '{eid}' references source '{src_ref}' but sources.yml is missing.")

        for cref in ev.get("claim_refs", []) or []:
            if cref not in claim_ids:
                errors.append(f"  Evidence '{eid}' claim_refs entry '{cref}' not found in claims.yml.")

        for cref in ev.get("supports", []) or []:
            if cref not in claim_ids:
                errors.append(f"  Evidence '{eid}' supports entry '{cref}' not found in claims.yml.")

        for cref in ev.get("contradicts", []) or []:
            if cref not in claim_ids:
                errors.append(f"  Evidence '{eid}' contradicts entry '{cref}' not found in claims.yml.")

    # Require sources.yml if evidence references sources
    evidence_source_refs = {e.get("source_ref", "") for e in evidence_items if e.get("source_ref")}
    if evidence_source_refs and not sources_data:
        errors.append("  sources.yml required because evidence items reference source IDs, but file is missing.")

    # Validate lifecycle redteam_ref points to an existing file
    if lifecycle_data:
        redteam_ref = lifecycle_data.get("redteam_ref", "")
        if redteam_ref:
            ref_path = case_dir / redteam_ref
            if not ref_path.exists():
                errors.append(f"  lifecycle.yml redteam_ref '{redteam_ref}' does not point to an existing file.")

    # Validate redteam assessment_ref points to an existing file
    if redteam_data:
        assessment_ref = redteam_data.get("assessment_ref", "")
        if assessment_ref:
            # assessment_ref may be relative to repo root or case dir
            ref_path = pathlib.Path(assessment_ref)
            if not ref_path.exists():
                # Try relative to case dir
                ref_path = case_dir / assessment_ref
            if not ref_path.exists():
                errors.append(
                    f"  redteam.yml assessment_ref '{assessment_ref}' does not point to an existing file."
                )

    return errors


def is_case_dir(path: pathlib.Path) -> bool:
    return any((path / f).exists() for f in CASE_FILES)


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)

    case_dirs = sorted(
        d for d in root.rglob("*")
        if d.is_dir() and "_template" not in d.parts and is_case_dir(d)
    )

    if not case_dirs:
        print(f"No case directories found under {root}")
        return 0

    total_errors = 0
    for case_dir in case_dirs:
        errors = validate_case(case_dir)
        if errors:
            print(f"FAIL {case_dir}:")
            for e in errors:
                print(e)
            total_errors += len(errors)
        else:
            print(f"OK   {case_dir}")

    if total_errors:
        print(f"\n{total_errors} reference error(s) found.")
        return 1

    print("\nAll case references valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
