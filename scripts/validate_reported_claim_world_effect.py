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
    *STRONG_EFFECT_RELATIONS,
}
# For high-strength relations (>= MAJOR_EFFECT_THRESHOLD), all strong-effect relation
# types are treated as major effects to prevent semantic bypass via relation-label
# switching (for example, high-strength `weakens` instead of `contradicts`).

STRENGTH_THRESHOLD = 0.6
MAJOR_EFFECT_THRESHOLD = 0.75
DIRECT_REPORTED_EVIDENCE_MARKER = "_direct_reported_evidence_marker"


ProvenanceToken = Tuple[str, Optional[str]]  # (marker, direct_evidence_id_or_none)


def load_yaml_file(path: Path) -> Tuple[Dict[str, Any], Optional[str]]:
    """Load YAML and return (content, error_message), with parse failures captured in error_message instead of raising."""
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


def normalize_source_refs(refs: Any) -> Set[str]:
    if not isinstance(refs, list):
        return set()
    return {src for src in refs if isinstance(src, str) and src}


def get_sources_by_id(sources_doc: Dict[str, Any]) -> Set[str]:
    sources_list = sources_doc.get("sources", [])
    if not isinstance(sources_list, list):
        return set()
    ids: Set[str] = set()
    for src in sources_list:
        if not isinstance(src, dict):
            continue
        source_id = src.get("source_id")
        if isinstance(source_id, str) and source_id:
            ids.add(source_id)
            continue
        alt_id = src.get("id")
        if isinstance(alt_id, str) and alt_id:
            ids.add(alt_id)
    return ids


def evidence_origin_sources(evidence: Dict[str, Any]) -> Set[str]:
    origins: Set[str] = set()
    singular = evidence.get("source_ref")
    if isinstance(singular, str) and singular:
        origins.add(singular)
    origins.update(normalize_source_refs(evidence.get("source_refs")))
    return origins


def is_reported_claim(claims_by_id: Dict[str, Dict[str, Any]], claim_id: str) -> bool:
    claim = claims_by_id.get(claim_id, {})
    return (
        claim.get("claim_kind") == "reported_claim"
        or claim.get("burden_profile") == "source_report"
    )


def is_world_claim(claims_by_id: Dict[str, Dict[str, Any]], claim_id: str) -> bool:
    claim = claims_by_id.get(claim_id, {})
    if (
        claim.get("claim_kind") == "reported_claim"
        or claim.get("burden_profile") == "source_report"
    ):
        return False
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


def get_major_effect_support_issue(
    obj: Dict[str, Any],
    known_source_ids: Set[str],
    derived_origin_sources: Set[str],
) -> Optional[str]:
    allowed_effect = obj.get("allowed_effect", "")
    independent_support = obj.get("independent_support_source_refs", [])
    if allowed_effect != "major_with_independent_support":
        return "allowed_effect must be 'major_with_independent_support'"
    if not (isinstance(independent_support, list) and bool(independent_support)):
        return "independent_support_source_refs must be a non-empty list"
    if any(not isinstance(src, str) or not src for src in independent_support):
        return "independent_support_source_refs must contain only non-empty strings"
    independent_set = set(s for s in independent_support if isinstance(s, str) and s)
    missing_source_ids = sorted(independent_set.difference(known_source_ids))
    if missing_source_ids:
        return (
            "independent_support_source_refs contains source id(s) missing in sources.yml: "
            + ", ".join(missing_source_ids)
        )
    origin_sources = obj.get("origin_source_refs")
    if origin_sources is not None and not isinstance(origin_sources, list):
        return "origin_source_refs must be a list when provided"
    if isinstance(origin_sources, list) and any(
        not isinstance(src, str) or not src for src in origin_sources
    ):
        return "origin_source_refs must contain only non-empty strings"

    if isinstance(origin_sources, list):
        effective_origin_sources = normalize_source_refs(origin_sources)
        overlap_label = "origin_source_refs"
    else:
        effective_origin_sources = derived_origin_sources
        overlap_label = "evidence-derived origin sources"

    if not effective_origin_sources:
        return "Cannot verify independence: origin sources are unknown."

    overlap = sorted(independent_set.intersection(effective_origin_sources))
    if overlap:
        return (
            f"independent_support_source_refs overlaps with {overlap_label}: "
            + ", ".join(overlap)
        )
    return None


def has_inference_provenance(
    inference_ledger: Dict[str, Any],
    world_claim_id: str,
    token: ProvenanceToken,
    relation_type: str,
    strength: float,
    known_source_ids: Set[str],
    derived_origin_sources: Set[str],
    failure_reasons: Optional[List[str]] = None,
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
            major_support_issue = (
                get_major_effect_support_issue(
                    inference, known_source_ids, derived_origin_sources
                )
                if major_relation
                else None
            )
            if major_support_issue is None:
                return True
            if failure_reasons is not None:
                failure_reasons.append(
                    f"inference-ledger top-level: {major_support_issue}"
                )

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
                major_support_issue = (
                    get_major_effect_support_issue(
                        step, known_source_ids, derived_origin_sources
                    )
                    if major_relation
                    else None
                )
                if major_support_issue is not None:
                    if failure_reasons is not None:
                        failure_reasons.append(
                            f"inference-ledger inference_step: {major_support_issue}"
                        )
                    continue
                return True

    return False


def has_argument_provenance(
    argument_provenance: Dict[str, Any],
    world_claim_id: str,
    token: ProvenanceToken,
    relation_type: str,
    strength: float,
    known_source_ids: Set[str],
    derived_origin_sources: Set[str],
    failure_reasons: Optional[List[str]] = None,
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
            major_support_issue = get_major_effect_support_issue(
                arg, known_source_ids, derived_origin_sources
            )
            if major_support_issue is not None:
                if failure_reasons is not None:
                    failure_reasons.append(
                        f"argument-provenance: {major_support_issue}"
                    )
                continue
            return True

        allowed_effect = arg.get("allowed_effect", "")
        if allowed_effect == "major_with_independent_support":
            major_support_issue = get_major_effect_support_issue(
                arg, known_source_ids, derived_origin_sources
            )
            if major_support_issue is not None:
                if failure_reasons is not None:
                    failure_reasons.append(
                        f"argument-provenance: {major_support_issue}"
                    )
                continue
            return True
        if allowed_effect in {"non_decisive", "uncertainty_only"}:
            return True

    return False


def describe_token(token: ProvenanceToken) -> str:
    marker, direct_evidence_id = token
    if marker == DIRECT_REPORTED_EVIDENCE_MARKER:
        return (
            f"direct source_report evidence id '{direct_evidence_id}' "
            f"(requires premise_evidence_refs match)"
        )
    return f"reported claim marker '{marker}' (requires premise_claim_refs match)"


def deduplicate_preserving_order(items: List[str]) -> List[str]:
    """Preserve first-seen order for stable, readable diagnostics (expects strings)."""
    return list(dict.fromkeys(items))


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
    sources, err = load_yaml_file(case_dir / "sources.yml")
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
    known_source_ids = get_sources_by_id(sources)

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
        report_derived_origin_sources: Set[str] = set()
        for evidence_id in evidence_ids:
            evidence = evidence_by_id.get(evidence_id)
            if not evidence:
                continue
            evidence_tokens = evidence_provenance_tokens(evidence, evidence_id, claims_by_id)
            if evidence_tokens:
                report_derived_ids.append(evidence_id)
                tokens.extend(evidence_tokens)
                report_derived_origin_sources.update(evidence_origin_sources(evidence))

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
        if strength_value is None:
            continue
        if strength_value < STRENGTH_THRESHOLD:
            continue

        unique_tokens: List[ProvenanceToken] = []
        seen_tokens: Set[ProvenanceToken] = set()
        for token in tokens:
            if token not in seen_tokens:
                seen_tokens.add(token)
                unique_tokens.append(token)

        missing_tokens: List[str] = []
        marker_issues: List[str] = []
        for token in unique_tokens:
            token_failures: List[str] = []
            has_valid = has_inference_provenance(
                inference_ledger,
                claim_ref,
                token,
                str(relation_type),
                strength_value,
                known_source_ids,
                report_derived_origin_sources,
                token_failures,
            ) or has_argument_provenance(
                argument_provenance,
                claim_ref,
                token,
                str(relation_type),
                strength_value,
                known_source_ids,
                report_derived_origin_sources,
                token_failures,
            )
            if has_valid:
                continue
            token_desc = describe_token(token)
            missing_tokens.append(token_desc)
            if token_failures:
                deduped_failures = deduplicate_preserving_order(token_failures)
                marker_issues.append(f"{token_desc}: {'; '.join(deduped_failures)}")

        if not missing_tokens:
            continue

        evidence_str = ", ".join(report_derived_ids)
        missing_tokens_str = "; ".join(missing_tokens)
        expected_fix = (
            "Provide matching premise_claim_refs or premise_evidence_refs with "
            "reported_to_world in inference-ledger.yml or argument-provenance.yml."
        )
        if is_major_relation(str(relation_type), strength_value):
            expected_fix += (
                " For major effects (strength >= 0.75), whichever artifact is used must also set "
                "allowed_effect='major_with_independent_support' and include non-empty "
                "independent_support_source_refs."
            )
        detail_suffix = (
            f" Detailed issues: {' | '.join(marker_issues)}."
            if marker_issues
            else ""
        )
        errors.append(
            f"{relations_file} relation_id={relation_id} claim_ref={claim_ref}: "
            f"report-derived evidence ({evidence_str}) uses relation_type={relation_type} "
            f"strength={strength_value} without valid provenance for marker(s): "
            f"{missing_tokens_str}. {expected_fix}{detail_suffix}"
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
