#!/usr/bin/env python3
"""Validate source-cluster-robustness.yml: stress-test verdict dependence on dominant source clusters.

Design principle: this validator does not decide which source is true. It enforces that
strong or negative verdicts on causal_claim claims openly declare their dependence on
source clusters, and that a knockout/stress test exists for each dominant cluster that
investigation-integrity.yml flags. Compromise scenarios are modeled as stress assumptions,
not as proof for any counter-hypothesis.
"""

import json
import pathlib
import re
import sys

from jsonschema_compat import jsonschema
import yaml

from case_compat import is_legacy_case, legacy_case_error

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "source-cluster-robustness.v1.schema.json"

ROBUSTNESS_FILENAME = "source-cluster-robustness.yml"
STRONG_OR_NEGATIVE_STATUSES = {"strongly_supported", "established", "contradicted"}
WORLD_CAUSAL_TYPES = {"causal_claim"}
ALLOWED_TREATMENTS = {
    "downgrade_to_reported_claim_only",
    "remove_from_world_claim_support",
    "require_independent_replication",
    "cap_negative_closure",
}
HIGH_FRAGILITY_THRESHOLD = 0.7
ASSESSMENT_FRAGILITY_TERMS = (
    "cluster dependency",
    "cluster dependence",
    "source-cluster dependence",
    "source cluster dependence",
    "fragility",
    "fragile",
    "knockout",
    # German equivalents (Fix 2)
    "fragilität",
    "fragil",
    "quellencluster",
    "quellen-cluster",
    "quellencluster-abhängigkeit",
    "cluster-abhängigkeit",
    "clusterabhängigkeit",
    "abhängigkeit vom cluster",
    "abhängigkeit vom quellencluster",
    "knockout-test",
    "stresstest",
    "stress-test",
)
# Conservative overreach phrases: compromise scenario must not be used as positive proof.
OVERREACH_PROOF_TERMS = (
    "proves",
    "proven",
    "beweist",
    "bewiesen",
    "therefore true",
    "deshalb wahr",
)
OVERREACH_COMPROMISE_TERMS = (
    "compromise",
    "compromised",
    "kompromittiert",
    "kompromittierung",
)
CASE_MARKERS = {
    "sources.yml",
    "claims.yml",
    "evidence-pack.yml",
    "investigation-integrity.yml",
    ROBUSTNESS_FILENAME,
}


def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


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


def schema_errors(payload: dict, schema: dict) -> list[str]:
    validator = jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())
    return [
        f"Schema error at {list(error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda err: list(err.absolute_path))
    ]


def _collect_ids(items, id_field: str) -> set[str]:
    ids: set[str] = set()
    if not isinstance(items, list):
        return ids
    for item in items:
        if isinstance(item, dict):
            value = item.get(id_field)
            if isinstance(value, str):
                ids.add(value)
    return ids


def _causal_strong_claims(claims_data: dict | None) -> list[dict]:
    out: list[dict] = []
    if not isinstance(claims_data, dict):
        return out
    claims = claims_data.get("claims", [])
    if not isinstance(claims, list):
        return out
    for claim in claims:
        if not isinstance(claim, dict):
            continue
        claim_type = claim.get("claim_type")
        claim_kind = claim.get("claim_kind", claim_type)
        status = claim.get("status")
        if not isinstance(status, str) or status not in STRONG_OR_NEGATIVE_STATUSES:
            continue
        # Source-report reported_claim closures are out of scope; this validator only
        # concerns world-causal verdicts.
        if claim_kind == "reported_claim":
            continue
        if claim_type in WORLD_CAUSAL_TYPES or claim_kind in WORLD_CAUSAL_TYPES:
            out.append(claim)
    return out


def _investigation_cluster_sources(integrity_data: dict | None) -> set[str]:
    """Return the union of source IDs flagged as source_cluster_refs in
    investigation-integrity.yml. These are the sources that integrity has
    already identified as belonging to dominant investigation clusters."""
    flagged: set[str] = set()
    if not isinstance(integrity_data, dict):
        return flagged
    investigations = integrity_data.get("investigations", [])
    if not isinstance(investigations, list):
        return flagged
    for inv in investigations:
        if not isinstance(inv, dict):
            continue
        refs = inv.get("source_cluster_refs")
        if isinstance(refs, list):
            for ref in refs:
                if isinstance(ref, str):
                    flagged.add(ref)
    return flagged


def _read_text(path: pathlib.Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _text_has_term(text: str, terms) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def _term_pattern(term: str) -> str:
    """Return a regex pattern that matches term as a whole word or phrase (not as a substring).
    For single words, uses \b word boundaries. For phrases, ensures no word characters
    immediately before or after the phrase to avoid partial substring matches."""
    escaped = re.escape(term)
    if " " in term:
        # Multi-word phrase: anchor at non-word-character boundaries on both sides.
        return r"(?<!\w)" + escaped + r"(?!\w)"
    return r"\b" + escaped + r"\b"


def _overreach_in_text(text: str) -> bool:
    """Return True if a compromise term and a proof term co-occur within a short
    window in the same text. Conservative: only flags when both appear nearby.
    Uses word/phrase boundary matching to avoid false positives on substrings
    (e.g., 'improves' will not match 'proves', 'uncompromised' will not match 'compromised')."""
    if not text:
        return False
    lower = text.lower()
    # Build compiled patterns for all compromise and proof terms.
    compiled_compromise = [
        re.compile(_term_pattern(t), re.IGNORECASE | re.UNICODE)
        for t in OVERREACH_COMPROMISE_TERMS
    ]
    compiled_proof = [
        re.compile(_term_pattern(t), re.IGNORECASE | re.UNICODE)
        for t in OVERREACH_PROOF_TERMS
    ]
    # Find every compromise term occurrence and check a +/- 120 char window for a proof term.
    for c_pat in compiled_compromise:
        for m in c_pat.finditer(lower):
            idx = m.start()
            window_start = max(0, idx - 120)
            window_end = min(len(lower), idx + len(m.group()) + 120)
            window = lower[window_start:window_end]
            if any(p_pat.search(window) for p_pat in compiled_proof):
                return True
    return False


def _load_evidence_pack(
    case_dir: pathlib.Path,
) -> tuple[dict[str, str], dict[str, set[str]], list[str]]:
    """Return (evidence_id_to_source_ref, claim_id_to_evidence_source_refs, errors).

    evidence_id_to_source_ref maps each evidence_id to its source_ref.
    claim_id_to_evidence_source_refs maps each claim_id to the set of source_refs
    backing it via evidence items whose claim_refs include that claim.
    Parse and type errors are returned in the errors list.
    """
    path = case_dir / "evidence-pack.yml"
    if not path.exists():
        return {}, {}, []
    data, err = safe_load_yaml(path)
    if err:
        return {}, {}, [f"Could not parse evidence-pack.yml: {err}"]
    if not isinstance(data, dict):
        return {}, {}, ["evidence-pack.yml must contain a YAML object."]
    evidence = data.get("evidence", [])
    if not isinstance(evidence, list):
        return {}, {}, ["evidence-pack.yml 'evidence' must be a list."]
    evidence_id_to_source_ref: dict[str, str] = {}
    claim_id_to_evidence_source_refs: dict[str, set[str]] = {}
    for item in evidence:
        if not isinstance(item, dict):
            continue
        eid = item.get("evidence_id")
        sref = item.get("source_ref")
        if not (isinstance(eid, str) and isinstance(sref, str)):
            continue
        evidence_id_to_source_ref[eid] = sref
        claim_refs = item.get("claim_refs", [])
        if isinstance(claim_refs, list):
            for cref in claim_refs:
                if isinstance(cref, str):
                    claim_id_to_evidence_source_refs.setdefault(cref, set()).add(sref)
    return evidence_id_to_source_ref, claim_id_to_evidence_source_refs, []


def _load_evidence_relations(case_dir: pathlib.Path) -> tuple[list[dict], list[str]]:
    """Return (relations, errors) from evidence-relations.yml.

    Parse and type errors are returned in the errors list.
    Returns an empty list and no errors when the file is absent.
    """
    path = case_dir / "evidence-relations.yml"
    if not path.exists():
        return [], []
    data, err = safe_load_yaml(path)
    if err:
        return [], [f"Could not parse evidence-relations.yml: {err}"]
    if not isinstance(data, dict):
        return [], ["evidence-relations.yml must contain a YAML object."]
    relations = data.get("relations", [])
    if not isinstance(relations, list):
        return [], ["evidence-relations.yml 'relations' must be a list."]
    return [r for r in relations if isinstance(r, dict)], []


SUPPORTING_RELATION_TYPES = {"supports_directly", "supports_indirectly"}
NEGATIVE_RELATION_TYPES = {"contradicts_directly"}
POSITIVE_KNOCKOUT_REST_VERDICTS = {"plausible", "strongly_supported", "established"}
STRONG_KNOCKOUT_REST_VERDICTS = {
    "established",
    "strongly_supported",
    "plausible",
    "contradicted",
}


def _remaining_support_floor_errors(
    *,
    verdict_without: str,
    claim_id: str,
    claim_kind: str | None,
    remaining_support: list[dict],
    remaining_contradiction: list[dict],
    removed_cluster_ref_list: list,
    test_id: str,
) -> list[str]:
    """Return strength-floor violations for a post-knockout verdict on a single claim.

    For causal_claim, enforce minimal remaining-relation structure for plausible /
    strongly_supported / established / contradicted verdict_without_cluster. For
    reported_claim, keep the legacy "at least one remaining support" check so that
    `reports` continues to count as remaining support without forcing world-causal
    direct-support semantics. Unknown evidence_refs and removed evidence_refs are
    already excluded by callers before invoking this helper.
    """
    errors: list[str] = []
    removed_sorted = sorted(str(ref) for ref in removed_cluster_ref_list)

    if verdict_without == "contradicted":
        if not remaining_contradiction:
            errors.append(
                f"verdict_without_cluster 'contradicted' not supported by remaining "
                f"direct contradiction relations for claim '{claim_id}' after removing "
                f"cluster(s) {removed_sorted} in knockout_test '{test_id}'."
            )
        return errors

    if verdict_without not in POSITIVE_KNOCKOUT_REST_VERDICTS:
        return errors

    if not remaining_support:
        errors.append(
            f"verdict_without_cluster '{verdict_without}' not supported by remaining "
            f"evidence relations for claim '{claim_id}' after removing cluster(s) "
            f"{removed_sorted} in knockout_test '{test_id}'."
        )
        return errors

    # reported_claim keeps the legacy "at least one remaining support" semantics;
    # `reports` already counts via the caller's effective_support_types.
    if claim_kind == "reported_claim":
        return errors

    direct_supports = [
        r for r in remaining_support if r.get("relation_type") == "supports_directly"
    ]

    if verdict_without == "plausible":
        # The "no remaining support" case is already handled above.
        return errors

    if verdict_without == "strongly_supported":
        if not direct_supports:
            errors.append(
                f"verdict_without_cluster 'strongly_supported' requires at least one "
                f"remaining supports_directly relation for claim '{claim_id}' after "
                f"removing cluster(s) {removed_sorted} in knockout_test '{test_id}'."
            )
        return errors

    if verdict_without == "established":
        unique_evidence_refs = {
            r.get("evidence_ref")
            for r in remaining_support
            if isinstance(r.get("evidence_ref"), str)
        }
        if (
            len(remaining_support) < 2
            or not direct_supports
            or len(unique_evidence_refs) < 2
        ):
            errors.append(
                f"verdict_without_cluster 'established' requires at least two remaining "
                f"support relations from at least two evidence_refs, including one "
                f"supports_directly relation, for claim '{claim_id}' after removing "
                f"cluster(s) {removed_sorted} in knockout_test '{test_id}'."
            )
        return errors

    return errors


def _resolve_claim_source_refs(
    claim: dict,
    evidence_id_to_source_ref: dict[str, str],
    claim_id_to_evidence_source_refs: dict[str, set[str]],
) -> set[str]:
    """Return the full set of source_refs attributable to a claim.

    Combines:
    1. Explicit claim.source_refs.
    2. claim.evidence_refs resolved through evidence_id_to_source_ref.
    3. Reverse lookup: all source_refs from evidence-pack items whose claim_refs include this claim.
    evidence_refs not found in evidence-pack.yml are silently ignored (not counted as coverage).
    """
    claim_id = claim.get("claim_id", "")
    result: set[str] = set()
    # 1. Explicit source_refs.
    srcs = claim.get("source_refs", [])
    if isinstance(srcs, list):
        result.update(s for s in srcs if isinstance(s, str))
    # 2. claim.evidence_refs resolved via evidence_id_to_source_ref.
    eids = claim.get("evidence_refs", [])
    if isinstance(eids, list):
        for eid in eids:
            if isinstance(eid, str) and eid in evidence_id_to_source_ref:
                result.add(evidence_id_to_source_ref[eid])
    # 3. Reverse lookup: evidence-pack items whose claim_refs include this claim.
    if isinstance(claim_id, str):
        result.update(claim_id_to_evidence_source_refs.get(claim_id, set()))
    return result


def validate_case(case_dir: pathlib.Path, schema: dict) -> list[str]:
    errors: list[str] = []

    # Legacy compatibility — malformed legacy case returns its error;
    # a valid legacy case is fully exempted from this validator's enforcement.
    legacy_error = legacy_case_error(case_dir)
    if legacy_error:
        return [legacy_error]
    if is_legacy_case(case_dir):
        return []

    sources_data, load_errors = load_optional_object(case_dir / "sources.yml", "sources.yml")
    errors.extend(load_errors)
    claims_data, load_errors = load_optional_object(case_dir / "claims.yml", "claims.yml")
    errors.extend(load_errors)
    integrity_data, load_errors = load_optional_object(
        case_dir / "investigation-integrity.yml", "investigation-integrity.yml"
    )
    errors.extend(load_errors)

    robustness_path = case_dir / ROBUSTNESS_FILENAME
    robustness_data: dict | None = None
    if robustness_path.exists():
        data, err = safe_load_yaml(robustness_path)
        if err:
            errors.append(f"Could not parse {ROBUSTNESS_FILENAME}: {err}")
        elif not isinstance(data, dict):
            errors.append(f"{ROBUSTNESS_FILENAME} must contain a YAML object.")
        else:
            robustness_data = data
            errors.extend(schema_errors(robustness_data, schema))

    causal_strong_claims = _causal_strong_claims(claims_data)
    integrity_cluster_sources = _investigation_cluster_sources(integrity_data)

    # Load evidence pack early; needed for claim-source derivation in Rule 2 and Rule 3.
    evidence_id_to_source_ref, claim_id_to_evidence_source_refs, evidence_pack_errors = (
        _load_evidence_pack(case_dir)
    )
    errors.extend(evidence_pack_errors)

    # Rule 2: Required artifact when integrity flags clusters AND strong/negative causal verdict
    # exists for claims whose resolved sources overlap the investigation-flagged cluster sources.
    # "Resolved sources" = explicit claim.source_refs ∪ claim.evidence_refs resolved via
    # evidence-pack ∪ evidence-pack claim_refs reversed to source_refs.
    # Conservative fallback: if a claim has no resolvable sources, it is treated as potentially
    # depending on flagged cluster sources.
    integrity_path = case_dir / "investigation-integrity.yml"
    if causal_strong_claims and integrity_path.exists() and integrity_cluster_sources:
        claims_requiring_robustness = []
        for claim in causal_strong_claims:
            cid = claim.get("claim_id", "?")
            resolved = _resolve_claim_source_refs(
                claim, evidence_id_to_source_ref, claim_id_to_evidence_source_refs
            )
            if not resolved or resolved & integrity_cluster_sources:
                claims_requiring_robustness.append(cid)
        if claims_requiring_robustness and not robustness_path.exists():
            claim_list = ", ".join(sorted(claims_requiring_robustness))
            errors.append(
                f"{ROBUSTNESS_FILENAME} required: causal_claim(s) {claim_list} carry a "
                "strongly_supported/established/contradicted status while investigation-integrity.yml "
                "declares source_cluster_refs; declare cluster dependency and knockout tests."
            )

    if robustness_data is None:
        return errors

    # Referential / structural extraction
    source_ids: set[str] = set()
    if isinstance(sources_data, dict):
        source_ids = _collect_ids(sources_data.get("sources"), "source_id")
    claim_ids: set[str] = set()
    # Fix 3: Build claim kind map to distinguish reported_claim from causal_claim.
    claim_kind_by_id: dict[str, str] = {}
    if isinstance(claims_data, dict):
        claim_ids = _collect_ids(claims_data.get("claims"), "claim_id")
        for claim in claims_data.get("claims", []) or []:
            if isinstance(claim, dict):
                cid = claim.get("claim_id")
                # claim_kind is preferred; fall back to claim_type for schema variants
                # that only declare claim_type (both fields are valid per schema history).
                kind = claim.get("claim_kind", claim.get("claim_type"))
                if isinstance(cid, str) and isinstance(kind, str):
                    claim_kind_by_id[cid] = kind

    clusters = robustness_data.get("clusters", [])
    if not isinstance(clusters, list):
        clusters = []
    knockout_tests = robustness_data.get("knockout_tests", [])
    if not isinstance(knockout_tests, list):
        knockout_tests = []

    # Fix 4: Duplicate cluster_id detection.
    seen_cluster_ids: list[str] = []
    for cluster in clusters:
        if isinstance(cluster, dict):
            cid = cluster.get("cluster_id")
            if isinstance(cid, str):
                if cid in seen_cluster_ids:
                    errors.append(f"Duplicate cluster_id '{cid}' in clusters.")
                else:
                    seen_cluster_ids.append(cid)

    # Fix 4: Duplicate test_id detection.
    seen_test_ids: list[str] = []
    for test in knockout_tests:
        if isinstance(test, dict):
            tid = test.get("test_id")
            if isinstance(tid, str):
                if tid in seen_test_ids:
                    errors.append(f"Duplicate test_id '{tid}' in knockout_tests.")
                else:
                    seen_test_ids.append(tid)

    cluster_by_id: dict[str, dict] = {}
    cluster_source_refs: dict[str, set[str]] = {}
    for cluster in clusters:
        if not isinstance(cluster, dict):
            continue
        cluster_id = cluster.get("cluster_id")
        if not isinstance(cluster_id, str):
            continue
        cluster_by_id[cluster_id] = cluster
        refs = cluster.get("source_refs", [])
        if isinstance(refs, list):
            # Fix 4: Duplicate source_refs within a cluster.
            seen_refs: list[str] = []
            for r in refs:
                if isinstance(r, str):
                    if r in seen_refs:
                        errors.append(
                            f"cluster '{cluster_id}' has duplicate source_ref '{r}'."
                        )
                    else:
                        seen_refs.append(r)
            cluster_source_refs[cluster_id] = {r for r in refs if isinstance(r, str)}
        else:
            cluster_source_refs[cluster_id] = set()

    # Rule 1: Referential integrity for clusters.
    for cluster_id, refs in cluster_source_refs.items():
        if source_ids:
            for ref in sorted(refs - source_ids):
                errors.append(
                    f"cluster '{cluster_id}' source_ref '{ref}' not found in sources.yml."
                )
        cluster = cluster_by_id.get(cluster_id, {})
        for scenario in cluster.get("compromise_scenarios", []) or []:
            if not isinstance(scenario, dict):
                continue
            # Rule 5: treatment discipline (also enforced by schema enum, kept for clarity).
            treatment = scenario.get("treatment")
            if isinstance(treatment, str) and treatment not in ALLOWED_TREATMENTS:
                errors.append(
                    f"cluster '{cluster_id}' compromise_scenario '{scenario.get('scenario_id', '?')}' "
                    f"has unknown treatment '{treatment}'."
                )
            affected = scenario.get("affected_claims", []) or []
            if isinstance(affected, list) and claim_ids:
                for cref in affected:
                    if isinstance(cref, str) and cref not in claim_ids:
                        errors.append(
                            f"cluster '{cluster_id}' compromise_scenario '{scenario.get('scenario_id', '?')}' "
                            f"affected_claim '{cref}' not found in claims.yml."
                        )
            # Rule 6: no overreach — compromise scenario may not be used as positive proof.
            for field in ("notes", "rationale", "premise"):
                text = scenario.get(field, "")
                if isinstance(text, str) and _overreach_in_text(text):
                    errors.append(
                        f"cluster '{cluster_id}' compromise_scenario '{scenario.get('scenario_id', '?')}' "
                        f"{field} appears to use a compromise assumption as positive proof; "
                        "a stress scenario is not evidence for a counter-hypothesis."
                    )

    # Rule 1 cont.: knockout test references.
    for test in knockout_tests:
        if not isinstance(test, dict):
            continue
        test_id = test.get("test_id", "?")
        removed = test.get("removed_cluster_refs", []) or []
        if isinstance(removed, list):
            # Fix 4: Duplicate removed_cluster_refs within a knockout test.
            seen_removed: list[str] = []
            for ref in removed:
                if isinstance(ref, str):
                    if ref in seen_removed:
                        errors.append(
                            f"knockout_test '{test_id}' has duplicate removed_cluster_ref '{ref}'."
                        )
                    else:
                        seen_removed.append(ref)
                    if ref not in cluster_by_id:
                        errors.append(
                            f"knockout_test '{test_id}' removed_cluster_ref '{ref}' is not a declared cluster."
                        )
        affected = test.get("affected_claims", []) or []
        if isinstance(affected, list):
            # Fix 4: Duplicate affected_claims within a knockout test.
            seen_affected: list[str] = []
            for cref in affected:
                if isinstance(cref, str):
                    if cref in seen_affected:
                        errors.append(
                            f"knockout_test '{test_id}' has duplicate affected_claim '{cref}'."
                        )
                    else:
                        seen_affected.append(cref)
            if claim_ids:
                for cref in affected:
                    if isinstance(cref, str) and cref not in claim_ids:
                        errors.append(
                            f"knockout_test '{test_id}' affected_claim '{cref}' not found in claims.yml."
                        )
        for field in ("notes", "rationale"):
            text = test.get(field, "")
            if isinstance(text, str) and _overreach_in_text(text):
                errors.append(
                    f"knockout_test '{test_id}' {field} appears to use a compromise assumption "
                    "as positive proof; knockout reasoning models fragility, not truth."
                )

    # Rule 3: strong-verdict fragility — for each strong causal claim, ensure a knockout test
    # exists that removes a cluster whose sources intersect investigation-integrity flagged sources.
    # Also: ALL flagged sources for a claim must be fully covered by declared clusters (partial
    # coverage is not enough).
    if causal_strong_claims and integrity_cluster_sources:
        # Build a reverse map: which sources are covered by at least one declared cluster?
        all_clustered_sources: set[str] = set()
        for refs in cluster_source_refs.values():
            all_clustered_sources.update(refs)

        for claim in causal_strong_claims:
            claim_id = claim.get("claim_id")
            if not isinstance(claim_id, str):
                continue
            # Resolved sources for this claim: explicit source_refs ∪ evidence_refs ∪ reverse
            # evidence-pack claim_refs. Unknown evidence_refs are silently excluded.
            claim_resolved_sources = _resolve_claim_source_refs(
                claim, evidence_id_to_source_ref, claim_id_to_evidence_source_refs
            )

            # Flagged sources: intersection of claim's resolved sources with investigation cluster sources.
            # Mixed-case fix: if resolved sources are known but none overlap the flagged cluster
            # sources, this claim does not depend on the flagged clusters — skip Rule 3 for it.
            # Conservative fallback: if no sources can be resolved at all, apply Rule 3 to all
            # integrity_cluster_sources to avoid silently missing real cluster dependencies.
            if claim_resolved_sources:
                flagged_sources = claim_resolved_sources & integrity_cluster_sources
                if not flagged_sources:
                    continue  # This claim has no overlap with investigation-flagged cluster sources.
            else:
                flagged_sources = integrity_cluster_sources

            # ALL flagged sources must be fully covered by declared clusters.
            uncovered = flagged_sources - all_clustered_sources
            if uncovered:
                errors.append(
                    f"causal_claim '{claim_id}' has status='{claim.get('status')}': "
                    f"flagged source(s) {sorted(uncovered)} are not covered by any declared cluster "
                    "in source-cluster-robustness.yml; partial coverage is not enough."
                )

            # Dominant clusters for this claim: clusters whose sources overlap the flagged sources
            # (i.e., the intersection of the claim's resolved sources with integrity_cluster_sources).
            dominant_clusters: set[str] = set()
            for cluster_id, refs in cluster_source_refs.items():
                if not (refs & flagged_sources):
                    continue
                dominant_clusters.add(cluster_id)
            if not dominant_clusters:
                errors.append(
                    f"causal_claim '{claim_id}' has status='{claim.get('status')}' and depends on "
                    "investigation-flagged source clusters, but no declared cluster covers those sources; "
                    "declare the dominant cluster(s) in source-cluster-robustness.yml."
                )
                continue
            covering_tests = []
            for test in knockout_tests:
                if not isinstance(test, dict):
                    continue
                removed = set(test.get("removed_cluster_refs", []) or [])
                affected = set(test.get("affected_claims", []) or [])
                if (removed & dominant_clusters) and claim_id in affected:
                    covering_tests.append(test)
            if not covering_tests:
                errors.append(
                    f"causal_claim '{claim_id}' has status='{claim.get('status')}' but no knockout_test "
                    f"removes a dominant cluster ({', '.join(sorted(dominant_clusters))}) affecting it."
                )
            else:
                # All dominant clusters must be covered — either all removed together in one test,
                # or each dominant cluster is removed in at least one test that affects this claim.
                fully_covered_at_once = any(
                    dominant_clusters <= set(t.get("removed_cluster_refs", []) or [])
                    for t in covering_tests
                    if isinstance(t, dict)
                )
                if not fully_covered_at_once:
                    tested_dominant: set[str] = set()
                    for t in covering_tests:
                        if isinstance(t, dict):
                            removed_set = set(t.get("removed_cluster_refs", []) or [])
                            tested_dominant.update(removed_set & dominant_clusters)
                    uncovered_dominant = dominant_clusters - tested_dominant
                    if uncovered_dominant:
                        errors.append(
                            f"causal_claim '{claim_id}' has status='{claim.get('status')}': "
                            f"dominant cluster(s) {sorted(uncovered_dominant)} are not covered by any "
                            "knockout_test affecting this claim; all dominant clusters must be individually "
                            "tested or all tested together in one knockout."
                        )

    # Rule 4: high fragility visibility.
    high_fragility_present = False
    for test in knockout_tests:
        if not isinstance(test, dict):
            continue
        score = test.get("fragility_score")
        if not isinstance(score, (int, float)) or score < HIGH_FRAGILITY_THRESHOLD:
            continue
        high_fragility_present = True
        notes = test.get("notes")
        rationale = test.get("rationale")
        has_inline_text = (isinstance(notes, str) and notes.strip()) or (
            isinstance(rationale, str) and rationale.strip()
        )
        if not has_inline_text:
            errors.append(
                f"knockout_test '{test.get('test_id', '?')}' has fragility_score>={HIGH_FRAGILITY_THRESHOLD} "
                "but no notes or rationale; high fragility must be explained."
            )

    if high_fragility_present:
        assessment_text = _read_text(case_dir / "assessment.md")
        if not _text_has_term(assessment_text, ASSESSMENT_FRAGILITY_TERMS):
            errors.append(
                "assessment.md must surface cluster dependency / fragility when a knockout_test "
                f"reports fragility_score>={HIGH_FRAGILITY_THRESHOLD}."
            )

    # Relational knockout check: use the already-loaded evidence_id_to_source_ref, and load
    # evidence-relations.yml (errors propagated into main errors list).
    evidence_map = evidence_id_to_source_ref  # alias for clarity in the relational section
    relations, relations_errors = _load_evidence_relations(case_dir)
    errors.extend(relations_errors)
    for test in knockout_tests:
        if not isinstance(test, dict):
            continue
        test_id = test.get("test_id", "?")
        verdict_without = test.get("verdict_without_cluster")
        if not isinstance(verdict_without, str):
            continue

        requires_relational_check = verdict_without in STRONG_KNOCKOUT_REST_VERDICTS
        if requires_relational_check and not evidence_map:
            errors.append(
                f"knockout_test '{test_id}' sets verdict_without_cluster '{verdict_without}' "
                "but evidence-pack.yml is missing or empty; cannot validate remaining evidence "
                "after cluster knockout."
            )
        if requires_relational_check and not relations:
            errors.append(
                f"knockout_test '{test_id}' sets verdict_without_cluster '{verdict_without}' "
                "but evidence-relations.yml is missing or empty; cannot validate remaining evidence "
                "after cluster knockout."
            )
        if requires_relational_check and (not evidence_map or not relations):
            continue

        removed_cluster_ref_list = test.get("removed_cluster_refs", []) or []
        if not isinstance(removed_cluster_ref_list, list):
            continue

        # Determine removed sources: all source_refs in removed clusters.
        removed_sources: set[str] = set()
        for cref in removed_cluster_ref_list:
            if isinstance(cref, str):
                removed_sources.update(cluster_source_refs.get(cref, set()))

        # Determine removed evidences: all evidence_ids whose source_ref is in removed_sources.
        removed_evidences: set[str] = {
            eid for eid, sref in evidence_map.items() if sref in removed_sources
        }

        affected = test.get("affected_claims", []) or []
        if not isinstance(affected, list):
            continue

        for claim_id in affected:
            if not isinstance(claim_id, str):
                continue

            claim_kind = claim_kind_by_id.get(claim_id)
            # reported_claim: `reports` counts as remaining support. World-causal
            # causal_claim verdicts do not get this allowance.
            if claim_kind == "reported_claim":
                effective_support_types = SUPPORTING_RELATION_TYPES | {"reports"}
            else:
                effective_support_types = SUPPORTING_RELATION_TYPES

            # Only count relations whose evidence_ref is known in evidence-pack.yml
            # and was not removed by the cluster knockout.
            remaining_support = [
                r for r in relations
                if r.get("claim_ref") == claim_id
                and r.get("relation_type") in effective_support_types
                and r.get("evidence_ref") in evidence_map
                and r.get("evidence_ref") not in removed_evidences
            ]
            remaining_contradiction = [
                r for r in relations
                if r.get("claim_ref") == claim_id
                and r.get("relation_type") in NEGATIVE_RELATION_TYPES
                and r.get("evidence_ref") in evidence_map
                and r.get("evidence_ref") not in removed_evidences
            ]

            errors.extend(
                _remaining_support_floor_errors(
                    verdict_without=verdict_without,
                    claim_id=claim_id,
                    claim_kind=claim_kind,
                    remaining_support=remaining_support,
                    remaining_contradiction=remaining_contradiction,
                    removed_cluster_ref_list=removed_cluster_ref_list,
                    test_id=test_id,
                )
            )

    return errors


def is_case_dir(path: pathlib.Path) -> bool:
    return any((path / marker).exists() for marker in CASE_MARKERS)


def discover_case_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    candidate_dirs = {root}
    for marker in CASE_MARKERS:
        candidate_dirs.update(p.parent for p in root.rglob(marker))
    return sorted(
        d for d in candidate_dirs if d.is_dir() and "_template" not in d.parts and is_case_dir(d)
    )


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    schema = load_schema()
    case_dirs = discover_case_dirs(root)
    if not case_dirs:
        print(f"No case directories found under {root}")
        return 0

    total_errors = 0
    for case_dir in case_dirs:
        errors = validate_case(case_dir, schema)
        if errors:
            print(f"FAIL {case_dir}:")
            for error in errors:
                print(f"  {error}")
            total_errors += len(errors)
        else:
            print(f"OK   {case_dir}")

    if total_errors:
        print(f"\n{total_errors} source-cluster-robustness error(s) found.")
        return 1

    print("\nAll source-cluster-robustness checks valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
