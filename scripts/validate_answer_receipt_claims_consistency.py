#!/usr/bin/env python3
"""Validate semantic consistency between answer-receipt.yml and claims.yml."""

from __future__ import annotations

import pathlib
import sys

import yaml

from case_compat import legacy_case_error

CASE_MARKERS = ("claims.yml", "evidence-relations.yml", "anomaly-ledger.yml", "investigation-integrity.yml")
TARGET_TASKS = {"case_building", "claim_audit", "source_comparison", "world_question"}
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


def is_sandbox_case(case_dir: pathlib.Path) -> bool:
    return "sandbox" in case_dir.parts


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


def _is_strong_claim_coverage_exempt(claim: dict, sources_by_id: dict[str, dict]) -> bool:
    if _is_reported_or_source_report_claim(claim):
        return True
    return _is_local_meta_claim(claim, sources_by_id)


def validate_case(case_dir: pathlib.Path) -> list[str]:
    errors: list[str] = []
    legacy_error = legacy_case_error(case_dir)
    if legacy_error:
        return [legacy_error]

    claims_path = case_dir / "claims.yml"
    receipt_path = case_dir / "answer-receipt.yml"
    assessment_path = case_dir / "assessment.md"
    sources_path = case_dir / "sources.yml"
    if not (claims_path.exists() and receipt_path.exists() and assessment_path.exists()):
        return errors

    claims_data, err = safe_load_yaml(claims_path)
    if err:
        return [f"Could not parse claims.yml: {err}"]
    receipt_data, err = safe_load_yaml(receipt_path)
    if err:
        return [f"Could not parse answer-receipt.yml: {err}"]

    sources_data = {}
    if sources_path.exists():
        sources_data, _ = safe_load_yaml(sources_path)
    sources = (sources_data or {}).get("sources", []) if isinstance(sources_data, dict) else []
    sources_by_id = {
        source.get("source_id"): source
        for source in sources
        if isinstance(source, dict) and isinstance(source.get("source_id"), str)
    }

    if not isinstance(claims_data, dict):
        return ["claims.yml must contain a YAML object."]
    if not isinstance(receipt_data, dict):
        return ["answer-receipt.yml must contain a YAML object."]

    task = receipt_data.get("task_classification")
    if task not in TARGET_TASKS:
        return errors

    claims = claims_data.get("claims", [])
    if not isinstance(claims, list):
        return ["claims.yml 'claims' must be a list."]
    verdicts = receipt_data.get("verdicts_used", []) or []
    if not isinstance(verdicts, list):
        return ["answer-receipt.yml verdicts_used must be a list."]

    claim_by_id = {
        claim.get("claim_id"): claim
        for claim in claims
        if isinstance(claim, dict) and isinstance(claim.get("claim_id"), str)
    }
    claims_with_status = [
        claim
        for claim in claim_by_id.values()
        if isinstance(claim.get("status"), str) and claim.get("status").strip()
    ]

    substantive_case = not is_sandbox_case(case_dir)
    if substantive_case and claims_with_status and not verdicts:
        errors.append(
            "answer-receipt.yml verdicts_used must be non-empty when claims.yml contains claims with status "
            f"for task_classification={task}."
        )

    verdict_claim_ids: set[str] = set()
    for verdict in verdicts:
        if not isinstance(verdict, dict):
            continue
        claim_id = verdict.get("claim_id")
        status = verdict.get("status")
        if not isinstance(claim_id, str):
            continue
        verdict_claim_ids.add(claim_id)
        claim = claim_by_id.get(claim_id)
        if claim is None:
            errors.append(f"answer-receipt.yml verdicts_used references unknown claim_id '{claim_id}'.")
            continue
        claim_status = claim.get("status")
        if status != claim_status:
            errors.append(
                f"status mismatch for claim_id '{claim_id}': answer-receipt.yml has '{status}', "
                f"claims.yml has '{claim_status}'."
            )

    strong_world_claims = [
        claim
        for claim in claims_with_status
        if claim.get("status") in STRONG_STATUSES and not _is_strong_claim_coverage_exempt(claim, sources_by_id)
    ]
    for claim in strong_world_claims:
        claim_id = claim.get("claim_id")
        if claim_id not in verdict_claim_ids:
            errors.append(
                f"strong claim '{claim_id}' (status={claim.get('status')}) must be present in answer-receipt.yml verdicts_used."
            )

    background_only = bool((receipt_data.get("external_research") or {}).get("background_knowledge_only", False))
    if substantive_case and background_only and strong_world_claims:
        strong_ids = ", ".join(sorted(claim.get("claim_id") for claim in strong_world_claims if claim.get("claim_id")))
        errors.append(
            "external_research.background_knowledge_only=true is incompatible with strong world-claim closure in claims.yml: "
            + strong_ids
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
        print(f"\n{total_errors} receipt-claims consistency error(s) found.")
        return 1
    print("\nAll receipt-claims consistency checks valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
