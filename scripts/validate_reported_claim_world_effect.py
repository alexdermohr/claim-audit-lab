#!/usr/bin/env python3
"""
Validate that reported claims and source reports are not used as strong
world effects without explicit provenance.

Reported claims (claim_kind: reported_claim or burden_profile: source_report)
must not be used as strong defeaters, alternative explanations, or supports
against world claims (causal_claim, comparative_claim, motive_claim, etc.)
unless justified by inference-ledger.yml or argument-provenance.yml.

This prevents the error class: reported X → X becomes strong world argument.

Supported artifact formats:
- evidence-relations.yml: both evidence_ref (singular) and evidence_refs (plural)
- inference-ledger.yml: top-level premise_claim_refs/forbidden_upgrades(s)_checked,
  and nested inference_steps[].premise_claim_refs/forbidden_upgrade(s)_checked
- argument-provenance.yml: arguments[].target_claim_ref / premise_claim_refs /
  forbidden_upgrade(s)_checked / independent_support_source_refs

Note: evidence is only detected as report-derived when its claim_refs contain
a reported_claim id. Evidence without claim_refs is not checked.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any

try:
    import yaml
except ImportError:
    print(
        "ERROR: PyYAML not found. Install with: pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)


# World claim types that can be targets of rules
WORLD_CLAIM_TYPES = {
    "causal_claim",
    "comparative_claim",
    "motive_claim",
    "narrative_claim",
    "beneficiary_claim",
    "factual_event_claim",
    "statistical_claim",
}

# Relations that indicate a claim is being used as a strong effect
STRONG_EFFECT_RELATIONS = {
    "alternative_explanation",
    "weakens",
    "contradicts_directly",
    "supports_directly",
    "supports_indirectly",
    "method_challenge",
}

STRENGTH_THRESHOLD = 0.6


def load_yaml_file(path: Path) -> Dict[str, Any]:
    """Load a YAML file, return empty dict if not found."""
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
            return content if isinstance(content, dict) else {}
    except Exception:
        return {}


def get_evidence_refs(relation: Dict[str, Any]) -> List[str]:
    """
    Get evidence refs from a relation entry.
    Supports both evidence_ref (singular string) and evidence_refs (list).
    When both are present, the results are merged and deduplicated.
    """
    refs: List[str] = []
    singular = relation.get("evidence_ref")
    if isinstance(singular, str) and singular:
        refs.append(singular)
    plural = relation.get("evidence_refs", [])
    if isinstance(plural, list):
        refs.extend(plural)
    seen: set = set()
    result: List[str] = []
    for ref in refs:
        if ref not in seen:
            seen.add(ref)
            result.append(ref)
    return result


def get_forbidden_upgrade_checks(obj: Dict[str, Any]) -> List[str]:
    """
    Get the list of forbidden upgrade checks from a dict.
    Supports both forbidden_upgrades_checked (plural) and forbidden_upgrade_checked (singular).
    """
    checks: set = set()
    plural = obj.get("forbidden_upgrades_checked", [])
    if isinstance(plural, list):
        checks.update(plural)
    singular = obj.get("forbidden_upgrade_checked", [])
    if isinstance(singular, list):
        checks.update(singular)
    return list(checks)


def is_reported_claim(claims_by_id: Dict[str, Dict], claim_id: str) -> bool:
    """Check if a claim is a reported_claim or source_report."""
    if claim_id not in claims_by_id:
        return False
    claim = claims_by_id[claim_id]
    return (
        claim.get("claim_kind") == "reported_claim"
        or claim.get("burden_profile") == "source_report"
    )


def is_world_claim(claims_by_id: Dict[str, Dict], claim_id: str) -> bool:
    """Check if a claim is a world claim (causal, comparative, etc.)."""
    if claim_id not in claims_by_id:
        return False
    claim = claims_by_id[claim_id]
    return (
        claim.get("claim_type") in WORLD_CLAIM_TYPES
        or claim.get("claim_kind") in WORLD_CLAIM_TYPES
    )


def evidence_references_reported_claim(
    evidence: Dict[str, Any], claims_by_id: Dict[str, Dict]
) -> bool:
    """
    Check if evidence references a reported claim via claim_refs.
    Returns True if any claim_ref points to a reported_claim.
    Note: evidence without claim_refs is not detected as report-derived.
    """
    claim_refs = evidence.get("claim_refs", [])
    if not isinstance(claim_refs, list):
        return False
    return any(is_reported_claim(claims_by_id, ref) for ref in claim_refs)


def has_inference_provenance(
    case_dir: Path, world_claim_id: str, reported_claim_id: str
) -> bool:
    """
    Check if inference-ledger.yml contains an entry that handles the
    reported_to_world transformation for this (world_claim, reported_claim) pair.

    Supports two formats:
    1. Top-level: inference.claim_ref + inference.premise_claim_refs + forbidden_upgrade(s)_checked
    2. Nested:    inference.claim_ref + inference.inference_steps[].premise_claim_refs +
                  inference_steps[].forbidden_upgrade(s)_checked
    """
    inference_file = case_dir / "inference-ledger.yml"
    if not inference_file.exists():
        return False

    ledger = load_yaml_file(inference_file)
    inferences = ledger.get("inferences", [])
    if not isinstance(inferences, list):
        return False

    for inference in inferences:
        if not isinstance(inference, dict):
            continue
        if inference.get("claim_ref") != world_claim_id:
            continue

        # Form 1: top-level premise_claim_refs + forbidden_upgrade(s)_checked
        top_premises = inference.get("premise_claim_refs", [])
        if not isinstance(top_premises, list):
            top_premises = []
        top_checks = get_forbidden_upgrade_checks(inference)
        if reported_claim_id in top_premises and "reported_to_world" in top_checks:
            return True

        # Form 2: nested inference_steps
        steps = inference.get("inference_steps", [])
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict):
                continue
            step_premises = step.get("premise_claim_refs", [])
            if not isinstance(step_premises, list):
                step_premises = []
            step_checks = get_forbidden_upgrade_checks(step)
            if reported_claim_id in step_premises and "reported_to_world" in step_checks:
                return True

    return False


def has_argument_provenance(
    case_dir: Path, world_claim_id: str, reported_claim_id: str
) -> bool:
    """
    Check if argument-provenance.yml contains a valid justified argument for
    the (world_claim, reported_claim) pair.

    An argument is valid when:
    - target_claim_ref matches world_claim_id
    - reported_claim_id is in premise_claim_refs
    - forbidden_upgrade(s)_checked contains reported_to_world
    - if allowed_effect == major_with_independent_support,
      independent_support_source_refs must be non-empty
    """
    prov_file = case_dir / "argument-provenance.yml"
    if not prov_file.exists():
        return False

    prov = load_yaml_file(prov_file)
    arguments = prov.get("arguments", [])
    if not isinstance(arguments, list):
        return False

    for arg in arguments:
        if not isinstance(arg, dict):
            continue
        if arg.get("target_claim_ref") != world_claim_id:
            continue
        premises = arg.get("premise_claim_refs", [])
        if not isinstance(premises, list):
            premises = []
        if reported_claim_id not in premises:
            continue
        checks = get_forbidden_upgrade_checks(arg)
        if "reported_to_world" not in checks:
            continue
        allowed_effect = arg.get("allowed_effect", "")
        if allowed_effect == "major_with_independent_support":
            indep = arg.get("independent_support_source_refs", [])
            if not isinstance(indep, list) or len(indep) == 0:
                continue
        return True

    return False


def discover_case_dirs(root: Path) -> List[Path]:
    """Discover case directories containing claims.yml, skipping _template."""
    return sorted({
        marker.parent for marker in root.rglob("claims.yml")
        if "_template" not in marker.parts
    })


def validate_case(case_dir: Path) -> List[str]:
    """
    Validate evidence-relations in a single case directory.
    Returns list of error messages (empty list if all valid).
    """
    errors: List[str] = []

    # Load claims
    claims_file = case_dir / "claims.yml"
    claims = load_yaml_file(claims_file)
    claims_list = claims.get("claims", [])

    claims_by_id: Dict[str, Dict] = {}
    if isinstance(claims_list, list):
        for claim in claims_list:
            if isinstance(claim, dict):
                claim_id = claim.get("claim_id")
                if claim_id:
                    claims_by_id[claim_id] = claim

    # Load evidence
    evidence_file = case_dir / "evidence-pack.yml"
    evidence_pack = load_yaml_file(evidence_file)
    evidence_list = evidence_pack.get("evidence", [])

    evidence_by_id: Dict[str, Dict] = {}
    if isinstance(evidence_list, list):
        for evidence in evidence_list:
            if isinstance(evidence, dict):
                evidence_id = evidence.get("evidence_id")
                if evidence_id:
                    evidence_by_id[evidence_id] = evidence

    # Load relations
    relations_file = case_dir / "evidence-relations.yml"
    relations = load_yaml_file(relations_file)
    relations_list = relations.get("relations", [])

    if not isinstance(relations_list, list):
        return errors

    for relation in relations_list:
        if not isinstance(relation, dict):
            continue

        relation_id = relation.get("relation_id", "unknown")
        claim_ref = relation.get("claim_ref", "")
        relation_type = relation.get("relation_type", "")
        strength = relation.get("strength")

        # Only check strong relations
        if strength is None or strength < STRENGTH_THRESHOLD:
            continue

        # Only check strong-effect relations
        if relation_type not in STRONG_EFFECT_RELATIONS:
            continue

        # Only check if target is a world claim
        if not is_world_claim(claims_by_id, claim_ref):
            continue

        # Collect all evidence refs (support both singular and plural)
        evid_ids = get_evidence_refs(relation)

        # Check if any evidence is report-derived
        report_derived_evidence_ids: List[str] = []
        for evid_id in evid_ids:
            if evid_id not in evidence_by_id:
                continue
            evidence = evidence_by_id[evid_id]
            if evidence_references_reported_claim(evidence, claims_by_id):
                report_derived_evidence_ids.append(evid_id)

        if not report_derived_evidence_ids:
            continue

        # Found: strong report-derived evidence against world claim.
        # Determine which reported claim is referenced.
        reported_claim_id = None
        for evid_id in report_derived_evidence_ids:
            evidence = evidence_by_id[evid_id]
            for ref in evidence.get("claim_refs", []):
                if is_reported_claim(claims_by_id, ref):
                    reported_claim_id = ref
                    break
            if reported_claim_id:
                break

        if not reported_claim_id:
            continue

        # Check if inference-ledger.yml or argument-provenance.yml handles this
        if has_inference_provenance(case_dir, claim_ref, reported_claim_id):
            continue
        if has_argument_provenance(case_dir, claim_ref, reported_claim_id):
            continue

        evidence_str = ", ".join(report_derived_evidence_ids)
        errors.append(
            f"{relations_file} relation_id={relation_id}: "
            f"report-derived evidence ({evidence_str}) is used as "
            f"{relation_type} strength={strength} against world claim {claim_ref} "
            f"without inference-ledger.yml or argument-provenance.yml proving "
            f"reported_to_world handling. "
            f"Reported claim: {reported_claim_id}."
        )

    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: validate_reported_claim_world_effect.py <cases_dir>",
            file=sys.stderr,
        )
        return 1

    cases_dir = Path(sys.argv[1])

    if not cases_dir.is_dir():
        print(f"ERROR: {cases_dir} is not a directory", file=sys.stderr)
        return 1

    case_dirs = discover_case_dirs(cases_dir)
    if not case_dirs:
        print(f"No claims.yml files found under {cases_dir}")
        return 0

    all_errors: List[str] = []
    for case_dir in case_dirs:
        errors = validate_case(case_dir)
        all_errors.extend(errors)

    if all_errors:
        for error in all_errors:
            print(error)
        return 1

    print("All reported-claim world-effect relations valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
