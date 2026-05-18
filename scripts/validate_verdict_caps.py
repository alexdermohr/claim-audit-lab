#!/usr/bin/env python3
"""Verdict caps: unresolved high-materiality defeaters block both strong positive and strong negative closure."""

import pathlib
import sys

import yaml

# Capped in all cases (positive and negative strong closure).
CAPPED_STATUSES = {"established", "strongly_supported", "contradicted"}
# source_report claims assert only that a source reported something, so positive
# strong closure is not inflated by a physical-mechanism defeater.  Negative
# closure (contradicted) is still capped because over-contradicting a
# source-report claim is equally asymmetric.
SOURCE_REPORT_EXEMPT_STATUSES = {"established", "strongly_supported"}
UNRESOLVED_DEFEATER_STATUSES = {"unresolved", "partially_resolved"}
HIGH_MATERIALITY = 0.75


def safe_load_yaml(path: pathlib.Path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except Exception as exc:
        return None, str(exc)


def load_optional_object(path: pathlib.Path, label: str) -> tuple[dict | None, list[str]]:
    if not path.exists():
        return None, []
    data, err = safe_load_yaml(path)
    if err:
        return None, [f"Could not parse {label}: {err}"]
    if not isinstance(data, dict):
        return None, [f"{label} must contain a YAML object."]
    return data, []


def is_source_report_claim(claim: dict) -> bool:
    return claim.get("claim_kind") == "reported_claim" and claim.get("burden_profile") == "source_report"


def validate_case(case_dir: pathlib.Path) -> list[str]:
    errors: list[str] = []
    claims_data, load_errors = load_optional_object(case_dir / "claims.yml", "claims.yml")
    errors.extend(load_errors)
    defeaters_data, load_errors = load_optional_object(case_dir / "model-defeaters.yml", "model-defeaters.yml")
    errors.extend(load_errors)

    if claims_data is None or defeaters_data is None:
        return errors

    claims = claims_data.get("claims", [])
    if not isinstance(claims, list):
        return errors
    claim_by_id = {
        claim.get("claim_id"): claim
        for claim in claims
        if isinstance(claim, dict) and isinstance(claim.get("claim_id"), str)
    }

    defeaters = defeaters_data.get("defeaters", [])
    if not isinstance(defeaters, list):
        return errors

    for defeater in defeaters:
        if not isinstance(defeater, dict):
            continue
        materiality = defeater.get("materiality")
        if not isinstance(materiality, (int, float)) or materiality < HIGH_MATERIALITY:
            continue
        if defeater.get("status") not in UNRESOLVED_DEFEATER_STATUSES:
            continue
        rebuttal = defeater.get("rebuttal_evidence_refs") or []
        if isinstance(rebuttal, list) and any(isinstance(r, str) and r.strip() for r in rebuttal):
            continue

        target_claim = defeater.get("target_claim_ref")
        if not isinstance(target_claim, str) or not target_claim:
            continue
        claim = claim_by_id.get(target_claim)
        if claim is None:
            continue
        status = claim.get("status")
        if status not in CAPPED_STATUSES:
            continue
        # source_report claims may keep positive strong closure: a defeater against
        # the physical mechanism does not invalidate the claim that a source reported it.
        if status in SOURCE_REPORT_EXEMPT_STATUSES and is_source_report_claim(claim):
            continue
        errors.append(
            f"claim '{target_claim}' status='{status}' is capped by unresolved high-materiality defeater "
            f"'{defeater.get('defeater_id', '?')}' (materiality={materiality}) without rebuttal_evidence_refs."
        )
    return errors


def discover_case_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted({marker.parent for marker in root.rglob("model-defeaters.yml") if "_template" not in marker.parts})


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    case_dirs = discover_case_dirs(root)
    if not case_dirs:
        print(f"No model-defeaters.yml files found under {root}")
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
        print(f"\n{total_errors} verdict-cap error(s) found.")
        return 1
    print("\nAll verdict caps valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
