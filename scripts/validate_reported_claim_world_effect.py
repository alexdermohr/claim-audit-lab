#!/usr/bin/env python3
"""
Validate that reported claims and source reports are not used as strong
world effects without explicit provenance.

Reported claims (claim_kind: reported_claim or burden_profile: source_report)
must not be used as strong defeaters, alternative explanations, or supports
against world claims (causal_claim, comparative_claim, motive_claim, etc.)
unless justified by inference-ledger or argument-provenance.

This prevents the error class: reported X → X becomes strong world argument.
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple

try:
    import yaml
except ImportError:
    print(
        "ERROR: PyYAML not found. Install with: pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)


# Evidence relations that are allowed without explicit provenance for reported/source claims
SAFE_RELATIONS = {
    "reports",
    "contextualizes",
    "source_position",
}

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


def is_reported_claim(claims_by_id: Dict[str, Dict], claim_id: str) -> bool:
    """Check if a claim is a reported_claim or source_report."""
    if claim_id not in claims_by_id:
        return False
    claim = claims_by_id[claim_id]
    claim_kind = claim.get("claim_kind", "")
    burden_profile = claim.get("burden_profile", "")
    return claim_kind == "reported_claim" or burden_profile == "source_report"


def is_world_claim(claims_by_id: Dict[str, Dict], claim_id: str) -> bool:
    """Check if a claim is a world claim (causal, comparative, etc.)."""
    if claim_id not in claims_by_id:
        return False
    claim = claims_by_id[claim_id]
    claim_type = claim.get("claim_type", "")
    claim_kind = claim.get("claim_kind", "")
    return claim_type in WORLD_CLAIM_TYPES or claim_kind in WORLD_CLAIM_TYPES


def evidence_references_reported_claim(
    evidence: Dict[str, Any], claims_by_id: Dict[str, Dict]
) -> bool:
    """
    Check if evidence primarily references a reported claim.
    If any claim_ref in this evidence is a reported claim, return True.
    """
    claim_refs = evidence.get("claim_refs", [])
    if not isinstance(claim_refs, list):
        return False
    return any(is_reported_claim(claims_by_id, ref) for ref in claim_refs)


def has_inference_provenance(
    case_dir: Path, world_claim_id: str, reported_claim_id: str
) -> bool:
    """
    Check if inference-ledger.yml contains a step that handles
    reported_to_world transformation for this pair.
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
        target = inference.get("claim_ref", "")
        premises = inference.get("premise_claim_refs", [])
        forbidden_upgrades_checked = inference.get("forbidden_upgrades_checked", [])

        if (
            target == world_claim_id
            and reported_claim_id in premises
            and "reported_to_world" in forbidden_upgrades_checked
        ):
            return True

    return False


def validate_case(case_dir: Path) -> List[str]:
    """
    Validate evidence-relations in a single case directory.
    Returns list of error messages (empty list if all valid).
    """
    errors = []

    # Load claims
    claims_file = case_dir / "claims.yml"
    claims = load_yaml_file(claims_file)
    claims_list = claims.get("claims", [])

    claims_by_id = {}
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

    evidence_by_id = {}
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
        evidence_refs = relation.get("evidence_refs", [])
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

        # Check if any evidence is report-derived
        report_derived_evidence_ids = []
        for evid_id in evidence_refs:
            if evid_id not in evidence_by_id:
                continue
            evidence = evidence_by_id[evid_id]
            if evidence_references_reported_claim(evidence, claims_by_id):
                report_derived_evidence_ids.append(evid_id)

        if not report_derived_evidence_ids:
            continue

        # Found: strong report-derived evidence against world claim.
        # Check if there's inference provenance.

        # Try to infer which reported claim is referenced
        reported_claim_id = None
        for evid_id in report_derived_evidence_ids:
            evidence = evidence_by_id[evid_id]
            claim_refs = evidence.get("claim_refs", [])
            for ref in claim_refs:
                if is_reported_claim(claims_by_id, ref):
                    reported_claim_id = ref
                    break
            if reported_claim_id:
                break

        if not reported_claim_id:
            continue

        # Check if inference-ledger handles this
        has_provenance = has_inference_provenance(
            case_dir, claim_ref, reported_claim_id
        )

        if not has_provenance:
            evidence_str = ", ".join(report_derived_evidence_ids)
            errors.append(
                f"{relations_file} relation_id={relation_id}: "
                f"report-derived evidence ({evidence_str}) is used as "
                f"{relation_type} strength={strength} against world claim {claim_ref} "
                f"without inference-ledger or argument-provenance proving "
                f"reported_to_world handling. "
                f"Reported claim: {reported_claim_id}."
            )

    return errors


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: validate_reported_claim_world_effect.py <cases_dir>",
            file=sys.stderr,
        )
        sys.exit(1)

    cases_dir = Path(sys.argv[1])

    if not cases_dir.is_dir():
        print(f"ERROR: {cases_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    all_errors = []

    # Find all case directories (those containing evidence-relations.yml or claims.yml)
    for claims_path in sorted(cases_dir.rglob("claims.yml")):
        case_dir = claims_path.parent
        errors = validate_case(case_dir)
        all_errors.extend(errors)

    if all_errors:
        for error in all_errors:
            print(error)
        sys.exit(1)
    else:
        print("All reported-claim world-effect relations valid.")
        sys.exit(0)


if __name__ == "__main__":
    main()
