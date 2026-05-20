#!/usr/bin/env python3
"""
Validate that reported claims and source reports are not used as strong
world effects without explicit provenance.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import yaml
except ImportError:
    print(
        "ERROR: PyYAML not found. Install with: pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)


WORLD_CLAIM_TYPES = {
    "causal_claim",
    "comparative_claim",
    "motive_claim",
    "narrative_claim",
    "beneficiary_claim",
    "factual_event_claim",
    "statistical_claim",
    "legal_claim",
    "capability_claim",
    "suppression_claim",
    "forecast_claim",
    "value_claim",
    "absence_claim",
}

STRONG_EFFECT_RELATIONS = {
    "alternative_explanation",
    "weakens",
    "contradicts",
    "contradicts_directly",
    "contradicts_indirectly",
    "supports",
    "supports_directly",
    "supports_indirectly",
    "method_challenge",
}

MAJOR_EFFECT_RELATIONS = {
    "alternative_explanation",
    "contradicts",
    "contradicts_directly",
    "method_challenge",
    "supports",
    "supports_directly",
}

STRENGTH_THRESHOLD = 0.6
MAJOR_EFFECT_THRESHOLD = 0.75
DIRECT_REPORTED_EVIDENCE_MARKER = "_direct_reported_evidence_marker"


ProvenanceToken = Tuple[str, Optional[str]]  # (marker, direct_evidence_id_or_none)


def load_yaml_file(path: Path) -> Tuple[Dict[str, Any], Optional[str]]:
    """Load YAML and return (content, error_message) instead of raising parse exceptions."""
    if not path.exists():
        return {}, None
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
    except Exception as exc:
        return {}, f"{path}: failed to parse YAML: {exc}"
    if content is None:
        return {}, None
    if not isinstance(content, dict):
        return {}, f"{path}: YAML root must be an object."
    return content, None


def get_evidence_refs(relation: Dict[str, Any]) -> List[str]:
    refs: List[str] = []
    singular = relation.get("evidence_ref")
    if isinstance(singular, str) and singular:
        refs.append(singular)
    plural = relation.get("evidence_refs", [])
    if isinstance(plural, list):
        refs.extend(ref for ref in plural if isinstance(ref, str) and ref)
    seen: Set[str] = set()
    deduped: List[str] = []
    for ref in refs:
        if ref not in seen:
            seen.add(ref)
            deduped.append(ref)
    return deduped


def get_forbidden_upgrade_checks(obj: Dict[str, Any]) -> List[str]:
    checks: Set[str] = set()
    plural = obj.get("forbidden_upgrades_checked", [])
    if isinstance(plural, list):
        checks.update(item for item in plural if isinstance(item, str))
    singular = obj.get("forbidden_upgrade_checked", [])
    if isinstance(singular, list):
        checks.update(item for item in singular if isinstance(item, str))
    return list(checks)


def is_reported_claim(claims_by_id: Dict[str, Dict[str, Any]], claim_id: str) -> bool:
    claim = claims_by_id.get(claim_id, {})
    return (
        claim.get("claim_kind") == "reported_claim"
        or claim.get("burden_profile") == "source_report"
    )


def is_world_claim(claims_by_id: Dict[str, Dict[str, Any]], claim_id: str) -> bool:
    claim = claims_by_id.get(claim_id, {})
    return (
        claim.get("claim_type") in WORLD_CLAIM_TYPES
        or claim.get("claim_kind") in WORLD_CLAIM_TYPES
    )


def parse_strength(
    relations_file: Path, relation_id: str, raw_strength: Any
) -> Tuple[Optional[float], Optional[str]]:
    try:
        return float(raw_strength), None
    except (TypeError, ValueError):
        return None, (
            f"{relations_file} relation_id={relation_id}: strength must be numeric; "
            f"got {raw_strength!r}."
        )


def is_major_relation(relation_type: str, strength: float) -> bool:
    return relation_type in MAJOR_EFFECT_RELATIONS and strength >= MAJOR_EFFECT_THRESHOLD


def evidence_provenance_tokens(
    evidence: Dict[str, Any],
    evidence_id: str,
    claims_by_id: Dict[str, Dict[str, Any]],
) -> List[ProvenanceToken]:
    tokens: List[ProvenanceToken] = []

    claim_refs = evidence.get("claim_refs", [])
    if isinstance(claim_refs, list):
        for ref in claim_refs:
            if isinstance(ref, str) and is_reported_claim(claims_by_id, ref):
                tokens.append((ref, None))

    if (
        evidence.get("burden_profile") == "source_report"
        or evidence.get("claim_kind") == "reported_claim"
    ) and not tokens:
        tokens.append((DIRECT_REPORTED_EVIDENCE_MARKER, evidence_id))

    seen: Set[ProvenanceToken] = set()
    deduped: List[ProvenanceToken] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            deduped.append(token)
    return deduped


def provenance_matches_premises(
    premise_claim_refs: Any,
    premise_evidence_refs: Any,
    token: ProvenanceToken,
) -> bool:
    marker, direct_evidence_id = token
    if marker == DIRECT_REPORTED_EVIDENCE_MARKER:
        return isinstance(premise_evidence_refs, list) and direct_evidence_id in premise_evidence_refs
    return isinstance(premise_claim_refs, list) and marker in premise_claim_refs


def has_required_major_effect_support(obj: Dict[str, Any]) -> bool:
    allowed_effect = obj.get("allowed_effect", "")
    independent_support = obj.get("independent_support_source_refs", [])
    has_independent_support = isinstance(independent_support, list) and bool(independent_support)
    return (
        allowed_effect == "major_with_independent_support"
        and has_independent_support
    )


def has_inference_provenance(
    inference_ledger: Dict[str, Any],
    world_claim_id: str,
    token: ProvenanceToken,
    relation_type: str,
    strength: float,
) -> bool:
    inferences = inference_ledger.get("inferences", [])
    if not isinstance(inferences, list):
        return False

    major_relation = is_major_relation(relation_type, strength)

    for inference in inferences:
        if not isinstance(inference, dict) or inference.get("claim_ref") != world_claim_id:
            continue

        top_claim_premises = inference.get("premise_claim_refs", [])
        top_evidence_premises = inference.get("premise_evidence_refs", [])
        top_checks = get_forbidden_upgrade_checks(inference)
        if (
            provenance_matches_premises(top_claim_premises, top_evidence_premises, token)
            and "reported_to_world" in top_checks
        ):
            if not major_relation or has_required_major_effect_support(inference):
                return True

        steps = inference.get("inference_steps", [])
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict):
                continue
            step_claim_premises = step.get("premise_claim_refs", [])
            step_evidence_premises = step.get("premise_evidence_refs", [])
            step_checks = get_forbidden_upgrade_checks(step)
            if (
                provenance_matches_premises(step_claim_premises, step_evidence_premises, token)
                and "reported_to_world" in step_checks
            ):
                if major_relation and not has_required_major_effect_support(step):
                    continue
                return True

    return False


def has_argument_provenance(
    argument_provenance: Dict[str, Any],
    world_claim_id: str,
    token: ProvenanceToken,
    relation_type: str,
    strength: float,
) -> bool:
    arguments = argument_provenance.get("arguments", [])
    if not isinstance(arguments, list):
        return False

    major_relation = is_major_relation(relation_type, strength)

    for arg in arguments:
        if not isinstance(arg, dict) or arg.get("target_claim_ref") != world_claim_id:
            continue

        premise_claim_refs = arg.get("premise_claim_refs", [])
        premise_evidence_refs = arg.get("premise_evidence_refs", [])
        if not provenance_matches_premises(premise_claim_refs, premise_evidence_refs, token):
            continue

        checks = get_forbidden_upgrade_checks(arg)
        if "reported_to_world" not in checks:
            continue

        if major_relation:
            if not has_required_major_effect_support(arg):
                continue
            return True

        allowed_effect = arg.get("allowed_effect", "")
        if allowed_effect == "major_with_independent_support":
            if not has_required_major_effect_support(arg):
                continue
            return True
        if allowed_effect in {"non_decisive", "uncertainty_only"}:
            return True

    return False


def discover_case_dirs(root: Path) -> List[Path]:
    return sorted({
        marker.parent for marker in root.rglob("claims.yml")
        if "_template" not in marker.parts
    })


def validate_case(case_dir: Path) -> List[str]:
    errors: List[str] = []

    claims, err = load_yaml_file(case_dir / "claims.yml")
    if err:
        return [err]
    evidence_pack, err = load_yaml_file(case_dir / "evidence-pack.yml")
    if err:
        return [err]
    relations, err = load_yaml_file(case_dir / "evidence-relations.yml")
    if err:
        return [err]
    inference_ledger, err = load_yaml_file(case_dir / "inference-ledger.yml")
    if err:
        return [err]
    argument_provenance, err = load_yaml_file(case_dir / "argument-provenance.yml")
    if err:
        return [err]

    claims_by_id: Dict[str, Dict[str, Any]] = {}
    claims_list = claims.get("claims", [])
    if isinstance(claims_list, list):
        for claim in claims_list:
            if isinstance(claim, dict):
                claim_id = claim.get("claim_id")
                if isinstance(claim_id, str) and claim_id:
                    claims_by_id[claim_id] = claim

    evidence_by_id: Dict[str, Dict[str, Any]] = {}
    evidence_list = evidence_pack.get("evidence", [])
    if isinstance(evidence_list, list):
        for evidence in evidence_list:
            if isinstance(evidence, dict):
                evidence_id = evidence.get("evidence_id")
                if isinstance(evidence_id, str) and evidence_id:
                    evidence_by_id[evidence_id] = evidence

    relations_file = case_dir / "evidence-relations.yml"
    relations_list = relations.get("relations", [])
    if not isinstance(relations_list, list):
        return errors

    for relation in relations_list:
        if not isinstance(relation, dict):
            continue

        relation_id = str(relation.get("relation_id", "unknown"))
        claim_ref = relation.get("claim_ref", "")
        relation_type = relation.get("relation_type", "")

        if relation_type not in STRONG_EFFECT_RELATIONS:
            continue
        if not isinstance(claim_ref, str) or not is_world_claim(claims_by_id, claim_ref):
            continue

        evidence_ids = get_evidence_refs(relation)
        report_derived_ids: List[str] = []
        tokens: List[ProvenanceToken] = []
        for evidence_id in evidence_ids:
            evidence = evidence_by_id.get(evidence_id)
            if not evidence:
                continue
            evidence_tokens = evidence_provenance_tokens(evidence, evidence_id, claims_by_id)
            if evidence_tokens:
                report_derived_ids.append(evidence_id)
                tokens.extend(evidence_tokens)

        if not report_derived_ids:
            continue

        strength_value, strength_error = parse_strength(
            relations_file, relation_id, relation.get("strength")
        )
        if strength_error:
            errors.append(strength_error)
            continue
        # Strength parsing happens only after relation/target/report-derived relevance checks.
        # Keep this guard so invalid/missing strengths fail relevant strong-effect relations only.
        if strength_value is None or strength_value < STRENGTH_THRESHOLD:
            continue

        unique_tokens: List[ProvenanceToken] = []
        seen_tokens: Set[ProvenanceToken] = set()
        for token in tokens:
            if token not in seen_tokens:
                seen_tokens.add(token)
                unique_tokens.append(token)

        all_markers_valid = all(
            has_inference_provenance(
                inference_ledger,
                claim_ref,
                token,
                str(relation_type),
                strength_value,
            )
            or has_argument_provenance(
                argument_provenance,
                claim_ref,
                token,
                str(relation_type),
                strength_value,
            )
            for token in unique_tokens
        )

        if all_markers_valid:
            continue

        evidence_str = ", ".join(report_derived_ids)
        errors.append(
            f"{relations_file} relation_id={relation_id}: report-derived evidence ({evidence_str}) "
            f"is used as {relation_type} strength={strength_value} against world claim {claim_ref} "
            f"without sufficient inference-ledger.yml or argument-provenance.yml support for "
            f"reported_to_world handling and allowed_effect compatibility."
        )

    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: validate_reported_claim_world_effect.py <cases_dir>", file=sys.stderr)
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
        all_errors.extend(validate_case(case_dir))

    if all_errors:
        for error in all_errors:
            print(error)
        return 1

    print("All reported-claim world-effect relations valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
