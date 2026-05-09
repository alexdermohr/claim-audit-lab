#!/usr/bin/env python3
"""Validate case-local cross-references: sources, evidence, claims, lifecycle, redteam."""

import sys
import pathlib
import yaml

STRONG_STATUSES = {"established", "strongly_supported"}
CASE_FILES = {"claims.yml", "sources.yml", "evidence-pack.yml", "lifecycle.yml", "redteam.yml"}


def safe_load_yaml(path: pathlib.Path):
    """Return (data, error_string). data is None on failure."""
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except Exception as e:
        return None, str(e)


def validate_case(case_dir: pathlib.Path) -> list[str]:
    errors = []

    claims_path = case_dir / "claims.yml"
    sources_path = case_dir / "sources.yml"
    evidence_path = case_dir / "evidence-pack.yml"
    lifecycle_path = case_dir / "lifecycle.yml"

    # --- Load claims ---
    claims_data = None
    if claims_path.exists():
        claims_data, err = safe_load_yaml(claims_path)
        if err:
            errors.append(f"  Could not parse claims.yml: {err}")
            claims_data = None
        elif not isinstance(claims_data, dict):
            errors.append("  claims.yml must contain a YAML object.")
            claims_data = None

    # --- Load sources ---
    sources_data = None
    if sources_path.exists():
        sources_data, err = safe_load_yaml(sources_path)
        if err:
            errors.append(f"  Could not parse sources.yml: {err}")
            sources_data = None
        elif not isinstance(sources_data, dict):
            errors.append("  sources.yml must contain a YAML object.")
            sources_data = None

    # --- Load evidence ---
    evidence_data = None
    if evidence_path.exists():
        evidence_data, err = safe_load_yaml(evidence_path)
        if err:
            errors.append(f"  Could not parse evidence-pack.yml: {err}")
            evidence_data = None
        elif not isinstance(evidence_data, dict):
            errors.append("  evidence-pack.yml must contain a YAML object.")
            evidence_data = None

    # --- Load lifecycle and resolve redteam_ref ---
    lifecycle_data = None
    if lifecycle_path.exists():
        lifecycle_data, err = safe_load_yaml(lifecycle_path)
        if err:
            errors.append(f"  Could not parse lifecycle.yml: {err}")
            lifecycle_data = None
        elif not isinstance(lifecycle_data, dict):
            errors.append("  lifecycle.yml must contain a YAML object.")
            lifecycle_data = None

    redteam_ref_name = "redteam.yml"
    if isinstance(lifecycle_data, dict) and lifecycle_data.get("redteam_ref"):
        redteam_ref_name = lifecycle_data["redteam_ref"]

    redteam_path = case_dir / redteam_ref_name
    redteam_data = None
    if redteam_path.exists():
        redteam_data, err = safe_load_yaml(redteam_path)
        if err:
            errors.append(f"  Could not parse {redteam_ref_name}: {err}")
            redteam_data = None
        elif not isinstance(redteam_data, dict):
            errors.append(f"  {redteam_ref_name} must contain a YAML object.")
            redteam_data = None

    # --- Build ID sets (only if data loaded successfully) ---
    claims = claims_data.get("claims", []) if isinstance(claims_data, dict) else []
    sources = sources_data.get("sources", []) if isinstance(sources_data, dict) else []
    evidence_items = evidence_data.get("evidence", []) if isinstance(evidence_data, dict) else []

    claim_ids = {c["claim_id"] for c in claims if isinstance(c, dict) and "claim_id" in c}
    source_ids = {s["source_id"] for s in sources if isinstance(s, dict) and "source_id" in s}
    evidence_ids = {e["evidence_id"] for e in evidence_items if isinstance(e, dict) and "evidence_id" in e}

    # --- Validate claims ---
    all_claim_source_refs: set[str] = set()
    all_claim_evidence_refs: set[str] = set()

    for claim in claims:
        if not isinstance(claim, dict):
            continue
        cid = claim.get("claim_id", "?")
        src_refs = claim.get("source_refs") or []
        ev_refs = claim.get("evidence_refs") or []
        status = claim.get("status", "")

        all_claim_source_refs.update(src_refs)
        all_claim_evidence_refs.update(ev_refs)

        if status in STRONG_STATUSES:
            if not src_refs:
                errors.append(f"  Claim '{cid}' status='{status}' requires non-empty source_refs.")
            if not ev_refs:
                errors.append(f"  Claim '{cid}' status='{status}' requires non-empty evidence_refs.")

        # Only resolve if the referenced file loaded successfully
        if sources_data is not None:
            for ref in src_refs:
                if ref not in source_ids:
                    errors.append(f"  Claim '{cid}' source_ref '{ref}' not found in sources.yml.")

        if evidence_data is not None:
            for ref in ev_refs:
                if ref not in evidence_ids:
                    errors.append(f"  Claim '{cid}' evidence_ref '{ref}' not found in evidence-pack.yml.")

    # Require sources.yml if any claim references sources and it's missing
    if all_claim_source_refs and not sources_path.exists():
        errors.append("  sources.yml required because claims reference source IDs, but file is missing.")

    # Require evidence-pack.yml if any claim references evidence and it's missing
    if all_claim_evidence_refs and not evidence_path.exists():
        errors.append("  evidence-pack.yml required because claims reference evidence IDs, but file is missing.")

    # --- Validate evidence items ---
    evidence_source_refs: set[str] = set()

    for ev in evidence_items:
        if not isinstance(ev, dict):
            continue
        eid = ev.get("evidence_id", "?")
        src_ref = ev.get("source_ref", "")

        if src_ref:
            evidence_source_refs.add(src_ref)
            if sources_data is not None and src_ref not in source_ids:
                errors.append(f"  Evidence '{eid}' source_ref '{src_ref}' not found in sources.yml.")

        if claims_data is not None:
            for cref in ev.get("claim_refs") or []:
                if cref not in claim_ids:
                    errors.append(f"  Evidence '{eid}' claim_refs entry '{cref}' not found in claims.yml.")
            for cref in ev.get("supports") or []:
                if cref not in claim_ids:
                    errors.append(f"  Evidence '{eid}' supports entry '{cref}' not found in claims.yml.")
            for cref in ev.get("contradicts") or []:
                if cref not in claim_ids:
                    errors.append(f"  Evidence '{eid}' contradicts entry '{cref}' not found in claims.yml.")

    if evidence_source_refs and not sources_path.exists():
        errors.append("  sources.yml required because evidence items reference source IDs, but file is missing.")

    # --- Validate lifecycle.redteam_ref points to existing file ---
    if isinstance(lifecycle_data, dict) and lifecycle_data.get("redteam_ref"):
        if not redteam_path.exists():
            errors.append(
                f"  lifecycle.yml redteam_ref '{redteam_ref_name}' does not point to an existing file."
            )

    # --- Validate redteam.assessment_ref points to existing file ---
    if isinstance(redteam_data, dict):
        assessment_ref = redteam_data.get("assessment_ref", "")
        if assessment_ref:
            ref_path = pathlib.Path(assessment_ref)
            if not ref_path.exists():
                ref_path = case_dir / assessment_ref
            if not ref_path.exists():
                errors.append(
                    f"  {redteam_ref_name} assessment_ref '{assessment_ref}' does not point to an existing file."
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
