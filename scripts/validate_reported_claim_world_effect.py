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
DIRECT_REPORTED_EVIDENCE = "__direct_reported_evidence__"


def load_yaml_file(path: Path) -> Tuple[Dict[str, Any], Optional[str]]:
    """Load a YAML file as an object, returning a parse error instead of swallowing it."""
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


def reported_claim_markers(
    evidence: Dict[str, Any], claims_by_id: Dict[str, Dict[str, Any]]
) -> List[str]:
    markers: List[str] = []
    claim_refs = evidence.get("claim_refs", [])
    if isinstance(claim_refs, list):
        for ref in claim_refs:
            if isinstance(ref, str) and is_reported_claim(claims_by_id, ref):
                markers.append(ref)

    if (
        evidence.get("burden_profile") == "source_report"
        or evidence.get("claim_kind") == "reported_claim"
    ) and not markers:
        markers.append(DIRECT_REPORTED_EVIDENCE)

    seen: Set[str] = set()
    return [marker for marker in markers if not (marker in seen or seen.add(marker))]


def provenance_matches_premises(
    premises: Any, reported_claim_marker: str
) -> bool:
    if reported_claim_marker == DIRECT_REPORTED_EVIDENCE:
        return True
    return isinstance(premises, list) and reported_claim_marker in premises


def has_inference_provenance(
    inference_ledger: Dict[str, Any], world_claim_id: str, reported_claim_marker: str
) -> bool:
    inferences = inference_ledger.get("inferences", [])
    if not isinstance(inferences, list):
        return False

    for inference in inferences:
        if not isinstance(inference, dict) or inference.get("claim_ref") != world_claim_id:
            continue

        top_premises = inference.get("premise_claim_refs", [])
        top_checks = get_forbidden_upgrade_checks(inference)
        if (
            provenance_matches_premises(top_premises, reported_claim_marker)
            and "reported_to_world" in top_checks
        ):
            return True

        steps = inference.get("inference_steps", [])
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict):
                continue
            step_premises = step.get("premise_claim_refs", [])
            step_checks = get_forbidden_upgrade_checks(step)
            if (
                provenance_matches_premises(step_premises, reported_claim_marker)
                and "reported_to_world" in step_checks
            ):
                return True

    return False


def has_argument_provenance(
    argument_provenance: Dict[str, Any],
    world_claim_id: str,
    reported_claim_marker: str,
    relation_type: str,
    strength: float,
) -> bool:
    arguments = argument_provenance.get("arguments", [])
    if not isinstance(arguments, list):
        return False

    major_relation = (
        relation_type in MAJOR_EFFECT_RELATIONS and strength >= MAJOR_EFFECT_THRESHOLD
    )

    for arg in arguments:
        if not isinstance(arg, dict) or arg.get("target_claim_ref") != world_claim_id:
            continue
        premises = arg.get("premise_claim_refs", [])
        if not provenance_matches_premises(premises, reported_claim_marker):
            continue
        checks = get_forbidden_upgrade_checks(arg)
        if "reported_to_world" not in checks:
            continue

        allowed_effect = arg.get("allowed_effect", "")
        independent_support = arg.get("independent_support_source_refs", [])
        has_independent_support = isinstance(independent_support, list) and bool(independent_support)

        if major_relation:
            if allowed_effect != "major_with_independent_support":
                continue
            if not has_independent_support:
                continue
            return True

        if allowed_effect == "major_with_independent_support" and not has_independent_support:
            continue
        if allowed_effect in {"non_decisive", "uncertainty_only", "major_with_independent_support"}:
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

        relation_id = relation.get("relation_id", "unknown")
        claim_ref = relation.get("claim_ref", "")
        relation_type = relation.get("relation_type", "")
        strength_value, strength_error = parse_strength(
            relations_file, str(relation_id), relation.get("strength")
        )
        if strength_error:
            errors.append(strength_error)
            continue
        assert strength_value is not None

        if strength_value < STRENGTH_THRESHOLD:
            continue
        if relation_type not in STRONG_EFFECT_RELATIONS:
            continue
        if not isinstance(claim_ref, str) or not is_world_claim(claims_by_id, claim_ref):
            continue

        evidence_ids = get_evidence_refs(relation)
        report_derived_ids: List[str] = []
        report_markers: List[str] = []
        for evidence_id in evidence_ids:
            evidence = evidence_by_id.get(evidence_id)
            if not evidence:
                continue
            markers = reported_claim_markers(evidence, claims_by_id)
            if markers:
                report_derived_ids.append(evidence_id)
                report_markers.extend(markers)

        if not report_derived_ids:
            continue

        unique_markers: List[str] = []
        seen_markers: Set[str] = set()
        for marker in report_markers:
            if marker not in seen_markers:
                seen_markers.add(marker)
                unique_markers.append(marker)

        has_valid_provenance = False
        for marker in unique_markers:
            if has_inference_provenance(inference_ledger, claim_ref, marker):
                has_valid_provenance = True
                break
            if has_argument_provenance(
                argument_provenance,
                claim_ref,
                marker,
                str(relation_type),
                strength_value,
            ):
                has_valid_provenance = True
                break

        if has_valid_provenance:
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
