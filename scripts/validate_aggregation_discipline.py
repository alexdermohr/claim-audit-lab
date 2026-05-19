#!/usr/bin/env python3
"""Block reported-claim aggregation closing on a world claim without bridge evidence.

See docs/aggregation-discipline.md.
"""

from __future__ import annotations

import pathlib
import sys

import yaml

from case_compat import legacy_case_error

CASE_MARKERS = ("claims.yml", "evidence-relations.yml", "anomaly-ledger.yml", "investigation-integrity.yml")

STRONG_STATUSES = {"strongly_supported", "established"}
WORLD_CLAIM_TYPES = {
    "factual_event_claim",
    "causal_claim",
    "narrative_claim",
    "motive_claim",
    "beneficiary_claim",
    "capability_claim",
}
REPORTS_RELATION_TYPE = "reports"
SOURCE_REPORT_BURDEN_PROFILE = "source_report"

# Threshold: if >= 80% of supporting relations are "reports", require bridge or robustness
REPORTS_DOMINANCE_THRESHOLD = 0.8


def safe_load_yaml(path: pathlib.Path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except Exception as exc:
        return None, str(exc)


def load_object(path: pathlib.Path):
    if not path.exists():
        return None
    data, err = safe_load_yaml(path)
    if err or not isinstance(data, dict):
        return None
    return data


def validate_case(case_dir: pathlib.Path) -> list[str]:
    errors: list[str] = []
    legacy_error = legacy_case_error(case_dir)
    if legacy_error:
        return [legacy_error]

    claims_data = load_object(case_dir / "claims.yml")
    relations_data = load_object(case_dir / "evidence-relations.yml")
    robustness_data = load_object(case_dir / "source-cluster-robustness.yml")

    if not claims_data:
        return []
    claims = [c for c in claims_data.get("claims", []) if isinstance(c, dict)]
    relations = []
    if relations_data:
        relations = [r for r in relations_data.get("relations", []) if isinstance(r, dict)]
    robustness_claims = set()
    if robustness_data:
        # Walk knockout_tests (the actual v1 schema) — if a claim is covered by
        # at least one knockout_test, the robustness audit is present.
        for entry in robustness_data.get("knockout_tests", []) or []:
            if not isinstance(entry, dict):
                continue
            for claim_ref in entry.get("affected_claims", []) or []:
                if isinstance(claim_ref, str):
                    robustness_claims.add(claim_ref)
        # Tolerate two alternative shapes used in older or simpler artifacts.
        for entry in robustness_data.get("robustness_tests", []) or []:
            if not isinstance(entry, dict):
                continue
            target = entry.get("claim_ref") or entry.get("target_claim")
            independence = entry.get("independence_verified", False)
            if target and independence:
                robustness_claims.add(target)
        for entry in robustness_data.get("clusters", []) or []:
            if not isinstance(entry, dict):
                continue
            target = entry.get("claim_ref") or entry.get("target_claim")
            independence = entry.get("independence_verified", False)
            if target and independence:
                robustness_claims.add(target)

    for claim in claims:
        claim_id = claim.get("claim_id")
        if not claim_id:
            continue
        claim_type = claim.get("claim_type")
        status = claim.get("status")
        claim_kind = claim.get("claim_kind", claim_type)
        burden_profile = claim.get("burden_profile")

        # Only check world-claim types with strong closure
        if claim_type not in WORLD_CLAIM_TYPES:
            continue
        if status not in STRONG_STATUSES:
            continue
        # Source-report-burden reported_claims are bounded by design; not aggregation candidates
        if burden_profile == SOURCE_REPORT_BURDEN_PROFILE and claim_kind == "reported_claim":
            continue

        claim_relations = [r for r in relations if r.get("claim_ref") == claim_id]
        if not claim_relations:
            # No relations declared for a strong-closure world claim is a separate problem;
            # other validators handle it.
            continue

        supporting = [
            r for r in claim_relations
            if r.get("relation_type") in {
                "reports", "supports_directly", "supports_indirectly", "contextualizes",
            }
        ]
        if not supporting:
            continue

        reports = [r for r in supporting if r.get("relation_type") == REPORTS_RELATION_TYPE]
        non_reports = [r for r in supporting if r.get("relation_type") != REPORTS_RELATION_TYPE]
        reports_share = len(reports) / len(supporting)

        if reports_share < REPORTS_DOMINANCE_THRESHOLD:
            continue  # mixed evidence base, not pure aggregation

        # Pure reports aggregation: require non-reports bridge OR robustness
        has_bridge = len(non_reports) >= 1
        has_robustness = claim_id in robustness_claims

        if not has_bridge and not has_robustness:
            errors.append(
                f"claim '{claim_id}' has status='{status}' but {reports_share:.0%} of supporting "
                f"relations are 'reports'-type with no non-'reports' bridge evidence and no "
                f"source-cluster-robustness entry with independence_verified=true; this is a "
                f"reported→world aggregation that the aggregation-discipline policy blocks"
            )

    return errors


def is_case_dir(path: pathlib.Path) -> bool:
    return any((path / marker).exists() for marker in CASE_MARKERS)


def discover_case_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    candidate_dirs = {root}
    for marker in CASE_MARKERS:
        candidate_dirs.update(path.parent for path in root.rglob(marker))
    return sorted(d for d in candidate_dirs if d.is_dir() and "_template" not in d.parts and is_case_dir(d))


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
        print(f"\n{total_errors} aggregation-discipline error(s) found.")
        return 1
    print("\nAll aggregation-discipline checks valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
