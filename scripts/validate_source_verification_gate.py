#!/usr/bin/env python3
"""Gate strong world-claim closure on source verification status."""

from __future__ import annotations

import pathlib
import sys

import yaml

from case_compat import legacy_case_error

CASE_MARKERS = ("claims.yml", "evidence-relations.yml", "anomaly-ledger.yml", "investigation-integrity.yml")
STRONG_STATUSES = {"established", "strongly_supported"}


def safe_load_yaml(path: pathlib.Path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except Exception as exc:
        return None, str(exc)


def is_case_dir(path: pathlib.Path) -> bool:
    return any((path / marker).exists() for marker in CASE_MARKERS)


def discover_case_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    candidate_dirs = {root}
    for marker in CASE_MARKERS:
        candidate_dirs.update(path.parent for path in root.rglob(marker))
    return sorted(d for d in candidate_dirs if d.is_dir() and "_template" not in d.parts and is_case_dir(d))


def _source_is_local(source: dict) -> bool:
    ref = str(source.get("url_or_ref", "")).strip().lower()
    if not ref:
        return True
    return not (ref.startswith("http://") or ref.startswith("https://"))


def _is_reported_or_source_report_claim(claim: dict) -> bool:
    return claim.get("claim_kind") == "reported_claim" or claim.get("burden_profile") == "source_report"


def _is_local_meta_claim(claim: dict, sources_by_id: dict[str, dict]) -> bool:
    if claim.get("claim_type") != "meta_claim":
        return False
    source_refs = claim.get("source_refs") or []
    if not isinstance(source_refs, list):
        return True
    for source_ref in source_refs:
        source = sources_by_id.get(source_ref)
        if isinstance(source, dict) and not _source_is_local(source):
            return False
    return True


def _is_verification_gate_exempt(claim: dict, sources_by_id: dict[str, dict]) -> bool:
    if _is_reported_or_source_report_claim(claim):
        return True
    return _is_local_meta_claim(claim, sources_by_id)


def _source_verification_status(source: dict) -> str | None:
    source_verification = source.get("source_verification")
    if isinstance(source_verification, dict):
        status = source_verification.get("status")
        if isinstance(status, str):
            return status

    notes = str(source.get("notes", ""))
    if "UNVERIFIED_REFERENCE" in notes.upper():
        return "unverified"
    return None


def validate_case(case_dir: pathlib.Path) -> list[str]:
    errors: list[str] = []
    legacy_error = legacy_case_error(case_dir)
    if legacy_error:
        return [legacy_error]

    claims_path = case_dir / "claims.yml"
    sources_path = case_dir / "sources.yml"
    if not (claims_path.exists() and sources_path.exists()):
        return errors

    claims_data, err = safe_load_yaml(claims_path)
    if err:
        return [f"Could not parse claims.yml: {err}"]
    sources_data, err = safe_load_yaml(sources_path)
    if err:
        return [f"Could not parse sources.yml: {err}"]

    if not isinstance(claims_data, dict):
        return ["claims.yml must contain a YAML object."]
    if not isinstance(sources_data, dict):
        return ["sources.yml must contain a YAML object."]

    claims = claims_data.get("claims", [])
    sources = sources_data.get("sources", [])
    if not isinstance(claims, list):
        return ["claims.yml 'claims' must be a list."]
    if not isinstance(sources, list):
        return ["sources.yml 'sources' must be a list."]

    sources_by_id = {
        source.get("source_id"): source
        for source in sources
        if isinstance(source, dict) and isinstance(source.get("source_id"), str)
    }

    for claim in claims:
        if not isinstance(claim, dict):
            continue
        claim_id = claim.get("claim_id", "?")
        status = claim.get("status")
        if status not in STRONG_STATUSES:
            continue
        if _is_verification_gate_exempt(claim, sources_by_id):
            continue

        source_refs = claim.get("source_refs") or []
        if not isinstance(source_refs, list):
            continue

        unverified_refs: list[str] = []
        for source_ref in source_refs:
            source = sources_by_id.get(source_ref)
            if not isinstance(source, dict):
                continue
            verification_status = _source_verification_status(source)
            if verification_status == "unverified":
                unverified_refs.append(source_ref)

        if unverified_refs:
            errors.append(
                f"claim '{claim_id}' status='{status}' references unverified sources: {sorted(set(unverified_refs))}. "
                "Strong world-claim closure requires verified/partially_verified source basis."
            )

    return errors


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    case_dirs = discover_case_dirs(root)
    if not case_dirs:
        print(f"No case directories found under {root}")
        return 0

    total_errors = 0
    for case_dir in case_dirs:
        errors = validate_case(case_dir)
        if errors:
            print(f"FAIL {case_dir}:")
            for error in errors:
                print(f"  {error}")
            total_errors += len(errors)
        else:
            print(f"OK   {case_dir}")

    if total_errors:
        print(f"\n{total_errors} source-verification gate error(s) found.")
        return 1
    print("\nAll source-verification gate checks valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
