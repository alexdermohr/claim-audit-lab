#!/usr/bin/env python3
"""Verdict caps: unresolved high-materiality defeaters block both strong positive and strong negative closure.

The scope of each cap is determined by defeater.verdict_effect.effect:
  prevents_strong_closure          → caps established, strongly_supported, contradicted
  prevents_strong_positive_closure → caps established, strongly_supported only
  prevents_strong_negative_closure → caps contradicted only
  downgrades_confidence            → no hard cap (lowers confidence, not a blocker)
  context_only                     → no cap
  missing verdict_effect or effect → defaults conservatively to prevents_strong_closure
"""

import pathlib
import sys

import yaml

POSITIVE_STRONG = {"established", "strongly_supported"}
NEGATIVE_STRONG = {"contradicted"}
ALL_STRONG = POSITIVE_STRONG | NEGATIVE_STRONG

# source_report claims assert only that a source reported something; a defeater
# against the physical mechanism does not invalidate that fact.  Positive strong
# closure is exempt; negative closure (contradicted) is still capped.
SOURCE_REPORT_EXEMPT_STATUSES = POSITIVE_STRONG

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
    # burden_profile is the schema-stable signal; claim_kind is optional.
    return claim.get("burden_profile") == "source_report"


def capped_statuses_for_effect(effect: str) -> set[str]:
    """Return the set of claim statuses that this defeater effect caps."""
    if effect in ("context_only", "downgrades_confidence"):
        return set()
    if effect == "prevents_strong_positive_closure":
        return POSITIVE_STRONG
    if effect == "prevents_strong_negative_closure":
        return NEGATIVE_STRONG
    # prevents_strong_closure and any unknown/missing value → conservative default.
    return ALL_STRONG


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

        effect = (defeater.get("verdict_effect") or {}).get("effect", "prevents_strong_closure")
        capped = capped_statuses_for_effect(effect)
        if status not in capped:
            continue
        # source_report claims retain positive strong closure; the defeater
        # targets the physical mechanism, not the act of reporting.
        if status in SOURCE_REPORT_EXEMPT_STATUSES and is_source_report_claim(claim):
            continue
        errors.append(
            f"claim '{target_claim}' status='{status}' is capped by unresolved high-materiality defeater "
            f"'{defeater.get('defeater_id', '?')}' (materiality={materiality}, effect='{effect}') "
            f"without rebuttal_evidence_refs."
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
