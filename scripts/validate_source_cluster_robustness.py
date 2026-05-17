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

from case_compat import legacy_case_error

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


def _overreach_in_text(text: str) -> bool:
    """Return True if a compromise term and a proof term co-occur within a short
    window in the same text. Conservative: only flags when both appear nearby."""
    if not text:
        return False
    lower = text.lower()
    # Find every compromise term occurrence and check a +/- 120 char window for a proof term.
    for c_term in OVERREACH_COMPROMISE_TERMS:
        start = 0
        while True:
            idx = lower.find(c_term, start)
            if idx < 0:
                break
            window_start = max(0, idx - 120)
            window_end = min(len(lower), idx + len(c_term) + 120)
            window = lower[window_start:window_end]
            if any(p in window for p in OVERREACH_PROOF_TERMS):
                return True
            start = idx + len(c_term)
    return False


def _load_evidence_pack(case_dir: pathlib.Path) -> dict[str, str]:
    """Return mapping evidence_id -> source_ref from evidence-pack.yml, or empty dict."""
    path = case_dir / "evidence-pack.yml"
    if not path.exists():
        return {}
    data, err = safe_load_yaml(path)
    if err or not isinstance(data, dict):
        return {}
    evidence = data.get("evidence", [])
    if not isinstance(evidence, list):
        return {}
    result: dict[str, str] = {}
    for item in evidence:
        if isinstance(item, dict):
            eid = item.get("evidence_id")
            sref = item.get("source_ref")
            if isinstance(eid, str) and isinstance(sref, str):
                result[eid] = sref
    return result


def _load_evidence_relations(case_dir: pathlib.Path) -> list[dict]:
    """Return list of evidence-relation dicts from evidence-relations.yml, or empty list."""
    path = case_dir / "evidence-relations.yml"
    if not path.exists():
        return []
    data, err = safe_load_yaml(path)
    if err or not isinstance(data, dict):
        return []
    relations = data.get("relations", [])
    if not isinstance(relations, list):
        return []
    return [r for r in relations if isinstance(r, dict)]


SUPPORTING_RELATION_TYPES = {"supports_directly", "supports_indirectly"}
NEGATIVE_RELATION_TYPES = {"contradicts_directly"}


def validate_case(case_dir: pathlib.Path, schema: dict) -> list[str]:
    errors: list[str] = []

    # Fix 1: Legacy compatibility — skip new errors for legacy-marked cases.
    legacy_error = legacy_case_error(case_dir)
    if legacy_error:
        return [legacy_error]

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

    # Rule 2: Required artifact when integrity flags clusters AND strong/negative causal verdict exists.
    integrity_path = case_dir / "investigation-integrity.yml"
    if (
        causal_strong_claims
        and integrity_path.exists()
        and integrity_cluster_sources
        and not robustness_path.exists()
    ):
        claim_list = ", ".join(sorted(claim.get("claim_id", "?") for claim in causal_strong_claims))
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
            # Sources backing this claim
            claim_source_refs: set[str] = set()
            srcs = claim.get("source_refs", [])
            if isinstance(srcs, list):
                claim_source_refs.update(s for s in srcs if isinstance(s, str))

            # Flagged sources: intersection of claim's source_refs with investigation cluster sources.
            # If claim has no source_refs field, fall back to all investigation cluster sources.
            if claim_source_refs:
                flagged_sources = claim_source_refs & integrity_cluster_sources
            else:
                flagged_sources = integrity_cluster_sources

            # Fix 3: ALL flagged sources must be fully covered by declared clusters.
            if flagged_sources:
                uncovered = flagged_sources - all_clustered_sources
                if uncovered:
                    errors.append(
                        f"causal_claim '{claim_id}' has status='{claim.get('status')}': "
                        f"flagged source(s) {sorted(uncovered)} are not covered by any declared cluster "
                        "in source-cluster-robustness.yml; partial coverage is not enough."
                    )

            # Dominant clusters for this claim: clusters whose sources overlap both
            # the investigation-flagged sources AND the claim's sources (if known).
            dominant_clusters: set[str] = set()
            for cluster_id, refs in cluster_source_refs.items():
                if not (refs & integrity_cluster_sources):
                    continue
                if claim_source_refs and not (refs & claim_source_refs):
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
                # Fix 2: All dominant clusters must be covered — either all removed together in one test,
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
    high_fragility_missing_text = False
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
            high_fragility_missing_text = True

    if high_fragility_present:
        assessment_text = _read_text(case_dir / "assessment.md")
        if not _text_has_term(assessment_text, ASSESSMENT_FRAGILITY_TERMS):
            errors.append(
                "assessment.md must surface cluster dependency / fragility when a knockout_test "
                f"reports fragility_score>={HIGH_FRAGILITY_THRESHOLD}."
            )

    # Fix 5: Minimal relational knockout check.
    # Only run when both evidence-pack.yml and evidence-relations.yml are present.
    evidence_map = _load_evidence_pack(case_dir)
    relations = _load_evidence_relations(case_dir)
    if evidence_map and relations:
        for test in knockout_tests:
            if not isinstance(test, dict):
                continue
            test_id = test.get("test_id", "?")
            verdict_without = test.get("verdict_without_cluster")
            if not isinstance(verdict_without, str):
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

                # Fix 1: Check negative verdict_without_cluster requires remaining contradicts_directly.
                if verdict_without == "contradicted":
                    remaining_contradiction = [
                        r for r in relations
                        if r.get("claim_ref") == claim_id
                        and r.get("relation_type") in NEGATIVE_RELATION_TYPES
                        # Fix 4: only count relations whose evidence_ref is known in evidence-pack.yml
                        and r.get("evidence_ref") in evidence_map
                        and r.get("evidence_ref") not in removed_evidences
                    ]
                    if not remaining_contradiction:
                        errors.append(
                            f"verdict_without_cluster 'contradicted' not supported by remaining "
                            f"direct contradiction relations for claim '{claim_id}' after removing "
                            f"cluster(s) {sorted(removed_cluster_ref_list)} in knockout_test '{test_id}'."
                        )
                    continue

                # Only check surviving positive verdicts.
                if verdict_without not in {"established", "strongly_supported", "plausible"}:
                    continue

                # Fix 3: For reported_claim, `reports` relation type also counts as remaining support.
                claim_kind = claim_kind_by_id.get(claim_id)
                if claim_kind == "reported_claim":
                    effective_support_types = SUPPORTING_RELATION_TYPES | {"reports"}
                else:
                    effective_support_types = SUPPORTING_RELATION_TYPES

                # Find remaining supporting relations for this claim.
                # Fix 4: only count relations whose evidence_ref is known in evidence-pack.yml.
                remaining_support = [
                    r for r in relations
                    if r.get("claim_ref") == claim_id
                    and r.get("relation_type") in effective_support_types
                    and r.get("evidence_ref") in evidence_map
                    and r.get("evidence_ref") not in removed_evidences
                ]
                if not remaining_support:
                    errors.append(
                        f"verdict_without_cluster '{verdict_without}' not supported by remaining "
                        f"evidence relations for claim '{claim_id}' after removing cluster(s) "
                        f"{sorted(removed_cluster_ref_list)} in knockout_test '{test_id}'."
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
