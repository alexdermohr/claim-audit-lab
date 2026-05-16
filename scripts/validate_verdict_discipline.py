#!/usr/bin/env python3
"""Validate verdict discipline using typed evidence relations and claim metadata."""

from collections import Counter, defaultdict
import json
import pathlib
import sys

from jsonschema_compat import jsonschema
import yaml
from case_compat import is_legacy_case, legacy_case_error, legacy_case_until

RELATION_SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "evidence-relation.v1.schema.json"
DIRECT_CONTRADICTION = "contradicts_directly"
WEAK_NEGATIVE_RELATIONS = {"alternative_explanation", "weakens", "undercuts", "missing_link"}
POSITIVE_RELATIONS = {"supports_directly", "supports_indirectly"}
LEGACY_SUPPORT_RELATIONS = POSITIVE_RELATIONS | {"reports"}
REPORTED_POSITIVE_RELATIONS = POSITIVE_RELATIONS | {"reports"}
OFFICIAL_SOURCE_TYPES = {"official_body", "government_report"}
STRONG_STATUSES = {"established", "strongly_supported"}
DOWNGRADED_STATUSES = {"weak", "contradicted", "speculative"}
WORLD_CAUSAL_KINDS = {"causal_claim"}


def load_schema() -> dict:
    with open(RELATION_SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def safe_load_yaml(path: pathlib.Path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except Exception as exc:
        return None, str(exc)




def schema_errors(payload: dict, schema: dict) -> list[str]:
    validator = jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())
    return [
        f"Schema error at {list(error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda err: list(err.absolute_path))
    ]


def load_optional_object(path: pathlib.Path, label: str) -> tuple[dict | None, list[str]]:
    if not path.exists():
        return None, []
    data, err = safe_load_yaml(path)
    if err:
        return None, [f"Could not parse {label}: {err}"]
    if not isinstance(data, dict):
        return None, [f"{label} must contain a YAML object."]
    return data, []


def validate_case(case_dir: pathlib.Path, relation_schema: dict) -> list[str]:
    errors: list[str] = []
    legacy_error = legacy_case_error(case_dir)
    if legacy_error:
        return [legacy_error]
    claims_path = case_dir / "claims.yml"
    relations_path = case_dir / "evidence-relations.yml"
    evidence_path = case_dir / "evidence-pack.yml"
    sources_path = case_dir / "sources.yml"
    hypotheses_path = case_dir / "hypotheses.yml"
    support_ledger_path = case_dir / "hypothesis-support-ledger.yml"

    claims_data, load_errors = load_optional_object(claims_path, "claims.yml")
    errors.extend(load_errors)
    if claims_data is None:
        if relations_path.exists():
            errors.append("evidence-relations.yml exists but claims.yml is missing or invalid.")
        return errors

    claims = claims_data.get("claims", [])
    claim_by_id = {
        claim.get("claim_id"): claim
        for claim in claims
        if isinstance(claim, dict) and claim.get("claim_id")
    }
    claim_ids = set(claim_by_id)

    evidence_ids: set[str] = set()
    evidence_by_id: dict[str, dict] = {}
    legacy_supports: list[tuple[str, str]] = []
    evidence_data, load_errors = load_optional_object(evidence_path, "evidence-pack.yml")
    errors.extend(load_errors)
    if claims_path.exists() and evidence_path.exists() and not relations_path.exists():
        errors.append("evidence-relations.yml required because claims.yml and evidence-pack.yml exist.")
    evidence_lookup_valid = isinstance(evidence_data, dict)
    if isinstance(evidence_data, dict):
        evidence_by_id = {
            item.get("evidence_id"): item
            for item in evidence_data.get("evidence", [])
            if isinstance(item, dict) and item.get("evidence_id")
        }
        evidence_ids = set(evidence_by_id)
        for evidence_ref, item in evidence_by_id.items():
            for claim_ref in item.get("supports") or []:
                legacy_supports.append((evidence_ref, claim_ref))

    source_types: dict[str, str] = {}
    sources_data, load_errors = load_optional_object(sources_path, "sources.yml")
    errors.extend(load_errors)
    if isinstance(sources_data, dict):
        source_types = {
            item.get("source_id"): item.get("source_type")
            for item in sources_data.get("sources", [])
            if isinstance(item, dict) and item.get("source_id")
        }

    legacy_contradicts: list[tuple[str, str]] = []
    if isinstance(evidence_data, dict):
        for evidence_ref, item in evidence_by_id.items():
            for claim_ref in item.get("contradicts") or []:
                legacy_contradicts.append((evidence_ref, claim_ref))

    relations_data = None
    relations: list[dict] = []
    relations_by_claim: dict[str, list[dict]] = defaultdict(list)
    relation_types_by_pair: dict[tuple[str, str], set[str]] = defaultdict(set)
    if relations_path.exists():
        relations_data, err = safe_load_yaml(relations_path)
        if err:
            errors.append(f"Could not parse evidence-relations.yml: {err}")
        elif not isinstance(relations_data, dict):
            errors.append("evidence-relations.yml must contain a YAML object.")
        else:
            relation_errors = schema_errors(relations_data, relation_schema)
            errors.extend(relation_errors)
            if not relation_errors:
                relations = relations_data.get("relations", [])
                relation_ids = [r.get("relation_id") for r in relations if isinstance(r, dict)]
                for relation_id, count in sorted(Counter(relation_ids).items()):
                    if count > 1:
                        errors.append(f"evidence-relations.yml has duplicate relation_id '{relation_id}'.")
                for relation in relations:
                    if not isinstance(relation, dict):
                        continue
                    rid = relation.get("relation_id", "?")
                    claim_ref = relation.get("claim_ref")
                    evidence_ref = relation.get("evidence_ref")
                    if claim_ref not in claim_ids:
                        errors.append(f"evidence relation '{rid}' claim_ref '{claim_ref}' not found in claims.yml.")
                    if not evidence_path.exists():
                        errors.append(
                            f"evidence relation '{rid}' references evidence_ref '{evidence_ref}', but evidence-pack.yml is missing."
                        )
                    elif evidence_lookup_valid and evidence_ref not in evidence_ids:
                        errors.append(f"evidence relation '{rid}' evidence_ref '{evidence_ref}' not found in evidence-pack.yml.")
                    claim = claim_by_id.get(claim_ref)
                    evidence = evidence_by_id.get(evidence_ref)
                    if claim and evidence:
                        claim_evidence_refs = set(claim.get("evidence_refs") or [])
                        evidence_claim_refs = set(evidence.get("claim_refs") or [])
                        if evidence_ref not in claim_evidence_refs or claim_ref not in evidence_claim_refs:
                            errors.append(
                                "Evidence relation must be mirrored by claim.evidence_refs and evidence.claim_refs "
                                f"for relation '{rid}'."
                            )
                    if relation.get("relation_type") == "contradicts_conditionally":
                        assumptions = relation.get("assumptions")
                        if not isinstance(assumptions, list) or not any(
                            isinstance(item, str) and item.strip() for item in assumptions
                        ):
                            errors.append(
                                f"conditional contradiction relation '{rid}' must document assumptions."
                            )
                        incompatible = relation.get("incompatible_proposition")
                        if not isinstance(incompatible, str) or not incompatible.strip():
                            errors.append(
                                f"conditional contradiction relation '{rid}' must name incompatible_proposition as a non-empty string."
                            )
                    relations_by_claim[claim_ref].append(relation)
                    relation_types_by_pair[(evidence_ref, claim_ref)].add(relation.get("relation_type"))

    for evidence_ref, claim_ref in legacy_supports:
        pair_types = relation_types_by_pair.get((evidence_ref, claim_ref), set())
        claim = claim_by_id.get(claim_ref, {})
        claim_kind = claim.get("claim_kind", claim.get("claim_type"))
        reports_allowed = claim_kind == "reported_claim" or claim.get("burden_profile") == "source_report"
        positive_pair_types = pair_types & LEGACY_SUPPORT_RELATIONS
        if not positive_pair_types or (positive_pair_types == {"reports"} and not reports_allowed):
            errors.append(
                "Legacy evidence-pack supports requires supports_directly/supports_indirectly typed evidence relation "
                "or reports for a reported/source-report claim "
                f"for evidence_ref '{evidence_ref}' and claim_ref '{claim_ref}'."
            )

    for evidence_ref, claim_ref in legacy_contradicts:
        pair_types = relation_types_by_pair.get((evidence_ref, claim_ref), set())
        if DIRECT_CONTRADICTION not in pair_types:
            errors.append(
                "Legacy evidence-pack contradicts requires contradicts_directly evidence relation "
                f"for evidence_ref '{evidence_ref}' and claim_ref '{claim_ref}'."
            )

    for claim_id, claim in claim_by_id.items():
        status = claim.get("status")
        claim_type = claim.get("claim_type")
        claim_kind = claim.get("claim_kind", claim_type)
        claim_relations = relations_by_claim.get(claim_id, [])
        relation_types = {r.get("relation_type") for r in claim_relations}

        if status in STRONG_STATUSES:
            positive_relation_types = REPORTED_POSITIVE_RELATIONS if claim_kind == "reported_claim" else POSITIVE_RELATIONS
            if not any(
                relation.get("relation_type") in positive_relation_types
                for relation in claim_relations
            ):
                errors.append(
                    f"Claim '{claim_id}' status='{status}' requires a positive typed evidence relation."
                )

        if status == "contradicted":
            direct_relations = [r for r in claim_relations if r.get("relation_type") == DIRECT_CONTRADICTION]
            if not direct_relations:
                errors.append(
                    f"Claim '{claim_id}' status='contradicted' requires at least one evidence relation with relation_type='contradicts_directly'."
                )
            for relation in direct_relations:
                if not relation.get("incompatible_proposition", "").strip():
                    errors.append(
                        f"Claim '{claim_id}' direct contradiction relation '{relation.get('relation_id', '?')}' must name incompatible_proposition."
                    )
            if relation_types and relation_types <= WEAK_NEGATIVE_RELATIONS:
                errors.append(
                    f"Claim '{claim_id}' cannot be 'contradicted' when all negative relations are weakens/undercuts/missing_link/alternative_explanation."
                )

        is_source_report_closure = claim_kind == "reported_claim" and claim.get("burden_profile") == "source_report"
        is_world_causal = (claim_kind in WORLD_CAUSAL_KINDS or claim_type in WORLD_CAUSAL_KINDS) and not is_source_report_closure

        if is_world_causal and status in (STRONG_STATUSES | {"contradicted"}):
            chain = claim.get("required_chain") or []
            if not claim.get("burden_profile") and not chain:
                errors.append(
                    f"Causal claim '{claim_id}' status='{status}' requires burden_profile or required_chain before strong or negative verdict."
                )
            missing_chain = [
                link for link in chain
                if isinstance(link, dict) and link.get("status") in {"missing", "contested"}
            ]
            if missing_chain:
                errors.append(
                    f"Causal claim '{claim_id}' status='{status}' has missing or contested required_chain links."
                )

            if status in STRONG_STATUSES:
                positive_evidence_refs = [
                    relation.get("evidence_ref")
                    for relation in claim_relations
                    if relation.get("relation_type") in POSITIVE_RELATIONS
                ]
                positive_source_refs = [
                    evidence_by_id[evidence_ref].get("source_ref")
                    for evidence_ref in positive_evidence_refs
                    if evidence_ref in evidence_by_id
                ]
                for source_ref in positive_source_refs:
                    if isinstance(sources_data, dict) and source_ref and source_ref not in source_types:
                        errors.append(
                            f"Positive evidence source_ref '{source_ref}' for claim '{claim_id}' not found in sources.yml."
                        )
                positive_source_types = [
                    source_types.get(source_ref)
                    for source_ref in positive_source_refs
                    if source_ref in source_types
                ]
                if positive_source_types and all(source_type in OFFICIAL_SOURCE_TYPES for source_type in positive_source_types):
                    errors.append(
                        f"World-causal claim '{claim_id}' status='{status}' is supported only by official/government source cluster."
                    )

                if claim_relations and {r.get("relation_type") for r in claim_relations} <= {"reports"}:
                    errors.append(
                        f"World-causal claim '{claim_id}' status='{status}' cannot be established only from source-report relations."
                    )

        if (
            claim_kind == "reported_claim"
            and claim_type == "causal_claim"
            and claim.get("burden_profile") != "source_report"
            and status in STRONG_STATUSES
        ):
            errors.append(
                f"Claim '{claim_id}' is claim_kind='reported_claim' but claim_type='causal_claim'; split source report from world-causal claim."
            )

        if claim_kind == "comparative_claim" and claim.get("claim_type") not in {"meta_claim", "narrative_claim", "causal_claim"}:
            errors.append(
                f"Comparative claim '{claim_id}' should use a compatible claim_type and must not be treated as direct falsification."
            )

    if hypotheses_path.exists():
        hypotheses_data, load_errors = load_optional_object(hypotheses_path, "hypotheses.yml")
        errors.extend(load_errors)
        if isinstance(hypotheses_data, dict):
            downgraded_hypotheses = [
                h for h in hypotheses_data.get("hypotheses", [])
                if isinstance(h, dict) and h.get("status") in DOWNGRADED_STATUSES
            ]
            if downgraded_hypotheses and not support_ledger_path.exists():
                errors.append(
                    "Downgraded hypotheses require hypothesis-support-ledger.yml before verdict discipline can pass."
                )

    return errors


def is_case_dir(path: pathlib.Path) -> bool:
    return any((path / name).exists() for name in ("claims.yml", "evidence-pack.yml", "assessment.md"))


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    relation_schema = load_schema()
    candidate_dirs = {root}
    for marker_name in ("claims.yml", "evidence-pack.yml", "assessment.md"):
        candidate_dirs.update(marker.parent for marker in root.rglob(marker_name))
    case_dirs = sorted(
        d for d in candidate_dirs
        if d.is_dir() and "_template" not in d.parts and is_case_dir(d)
    )

    if not case_dirs:
        print(f"No verdict-discipline case directories found under {root}")
        return 0

    total_errors = 0
    for case_dir in case_dirs:
        legacy_error = legacy_case_error(case_dir)
        if legacy_error:
            print(f"FAIL {case_dir}:")
            print(f"  {legacy_error}")
            total_errors += 1
            continue
        if is_legacy_case(case_dir):
            print(
                f"LEGACY {case_dir}: marker valid until {legacy_case_until(case_dir)}; "
                "verdict discipline still enforced"
            )
        errors = validate_case(case_dir, relation_schema)
        if errors:
            print(f"FAIL {case_dir}:")
            for error in errors:
                print(f"  {error}")
            total_errors += len(errors)
        else:
            print(f"OK   {case_dir}")

    if total_errors:
        print(f"\n{total_errors} verdict-discipline error(s) found.")
        return 1

    print("\nAll verdict-discipline checks valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
