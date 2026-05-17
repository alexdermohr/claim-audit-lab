#!/usr/bin/env python3
"""Block overclosure: weak negative operations must not become direct contradiction."""

from __future__ import annotations

from collections import defaultdict
import pathlib
import re
import sys

import yaml

from case_compat import legacy_case_error

CASE_MARKERS = ("claims.yml", "evidence-relations.yml", "anomaly-ledger.yml", "investigation-integrity.yml")
STRONG_OR_NEGATIVE_STATUSES = {"strongly_supported", "established", "contradicted"}
DIRECT_CONTRADICTION = "contradicts_directly"
WORLD_CAUSAL_KINDS = {"causal_claim"}
HIGH_MATERIALITY_THRESHOLD = 0.7
UNRESOLVED_STATUSES = {"unresolved", "partially_resolved"}

CO_CAUSATION_TERMS = (
    "mitverursachte",
    "mitverursacht",
    "contributed",
    "contributes",
    "co-cause",
    "co-causal",
    "co-causation",
    "partial cause",
    "partly caused",
    "alongside other causes",
)

OVERCLOSURE_PATTERNS = (
    r"stronger\s+(?:alternative|primary|main)\s+explanation",
    r"better\s+explanation",
    r"better\s+explained",
    r"alternative\s+explanation",
    r"alternatively\s+accounted\s+for",
    r"no\s+(?:positive\s+)?evidence\s+found",
    r"no\s+collected(?:\s+.*)?\s+evidence",
    r"no\s+observed(?:\s+.*)?\s+evidence",
    r"no\s+direct\s+evidence",
    r"no\s+positive\s+proof",
    r"directly\s+absent",
    r"not\s+found\s+in\s+(?:the\s+)?evidence\s+pack",
    r"missing\s+(?:positive\s+)?evidence",
    r"missing\s+link",
    r"lacks?\s+(?:(?:a|an)\s+)?(?:.*\s+)?bridge",
    r"lacks?\s+(?:(?:a|an)\s+)?(?:.*\s+)?mechanism",
    r"causal\s+bridge\s+(?:is\s+)?missing",
    r"not\s+necessary",
    r"official\s+non[-\s]?corroboration",
    r"non[-\s]?corroboration",
    r"no\s+corroborat(?:ed|ing)\s+evidence",
    r"not\s+corroborated",
    r"failed\s+to\s+corroborate",
    r"non[-\s]?corroborating",
    r"method\s+gap",
    r"methodological\s+gap",
    r"non[-\s]?test",
    r"absence\s+of\s+evidence",
    r"besser\s+erkl[aä]rt",
    r"bessere\s+erkl[aä]rung",
    r"st[aä]rkere\s+alternativerkl[aä]rung",
    r"keine\s+evidenz\s+gefunden",
    r"kein\s+positiver\s+nachweis",
    r"keine\s+belege",
    r"keine\s+gesammelte\s+evidenz",
    r"nicht\s+korroboriert",
    r"keine\s+korroborierenden\s+belege",
    r"fehlende\s+kausalbr[uü]cke",
    r"kausalbr[uü]cke\s+fehlt",
    r"fehlender\s+mechanismus",
    r"nichttest",
    r"nicht\s+getestet",
    r"methodenl[uü]cke",
    r"abwesenheit\s+von\s+evidenz",
    r"nicht\s+notwendig",
)

SUFFICIENT_DIRECT_EXCLUSION_PATTERNS = (
    r"directly\s+rules?\s+out",
    r"rules?\s+out",
    r"ruled\s+out",
    r"excludes?",
    r"excluded",
    r"physically\s+impossible",
    r"physical\s+impossibility",
    r"physikalisch\s+unm[oö]glich",
    r"temporally\s+impossible",
    r"temporal\s+exclusion",
    r"direct\s+temporal\s+exclusion",
    r"zeitlich\s+unm[oö]glich",
    r"direkte\s+zeitliche\s+exklusion",
    r"cannot\s+have\s+occurred",
    r"could\s+not\s+have\s+occurred",
    r"cannot\s+have",
    r"could\s+not\s+have",
    r"kann\s+nicht\s+stattgefunden\s+haben",
    r"mutually\s+exclusive",
    r"gegenseitig\s+ausschlie[ßs]end",
    r"schlie[ßs]t\s+aus",
    r"schlossen\s+aus",
    r"precludes?",
)

NEGATED_DIRECT_EXCLUSION_PATTERNS = (
    r"does\s+not\s+(?:.*\s+)?rule\s+out",
    r"do\s+not\s+(?:.*\s+)?rule\s+out",
    r"did\s+not\s+(?:.*\s+)?rule\s+out",
    r"not\s+rule\s+out",
    r"not\s+ruled\s+out",
    r"does\s+not\s+(?:.*\s+)?exclude",
    r"do\s+not\s+(?:.*\s+)?exclude",
    r"did\s+not\s+(?:.*\s+)?exclude",
    r"not\s+excluded",
    r"not\s+impossible",
    r"not\s+physically\s+impossible",
    r"not\s+temporally\s+impossible",
    r"not\s+mutually\s+exclusive",
    r"cannot\s+exclude",
    r"could\s+not\s+exclude",
    r"does\s+not\s+(?:.*\s+)?preclude",
    r"do\s+not\s+(?:.*\s+)?preclude",
    r"not\s+precluded",
    r"schlie(?:ß|ss|s)t\s+nicht\s+aus",
    r"schlie(?:ß|ss|s)t\s+.*\s+nicht\s+aus",
    r"schlie(?:ß|ss|s)en\s+nicht\s+aus",
    r"schlie(?:ß|ss|s)en\s+.*\s+nicht\s+aus",
    r"nicht\s+ausgeschlossen",
    r"nicht\s+unm[oö]glich",
    r"nicht\s+physikalisch\s+unm[oö]glich",
    r"nicht\s+zeitlich\s+unm[oö]glich",
    r"nicht\s+gegenseitig\s+ausschlie[ßs]end",
    r"kann\s+(?:.*\s+)?nicht\s+ausschlie(?:ß|ss|s)en",
    r"k[oö]nnen\s+(?:.*\s+)?nicht\s+ausschlie(?:ß|ss|s)en",
    r"l[aä]sst\s+offen",
)


def safe_load_yaml(path: pathlib.Path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except Exception as exc:  # pragma: no cover - exercised through CLI-style tests elsewhere
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


def text_from(*parts) -> str:
    chunks: list[str] = []
    for part in parts:
        if isinstance(part, str):
            chunks.append(part)
        elif isinstance(part, list):
            chunks.extend(item for item in part if isinstance(item, str))
        elif isinstance(part, dict):
            chunks.extend(str(value) for value in part.values() if isinstance(value, (str, int, float)))
    return " ".join(chunks).lower()


def has_pattern(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def contains_overclosure_operation(text: str) -> bool:
    return has_pattern(text, OVERCLOSURE_PATTERNS)


def contains_negated_direct_exclusion(text: str) -> bool:
    return has_pattern(text, NEGATED_DIRECT_EXCLUSION_PATTERNS)


def sentence_containing(text: str, start: int, end: int) -> str:
    left_candidates = [text.rfind(mark, 0, start) for mark in ".!?;:"]
    right_candidates = [text.find(mark, end) for mark in ".!?;:"]
    left = max(left_candidates) + 1
    right_positions = [position for position in right_candidates if position != -1]
    right = min(right_positions) + 1 if right_positions else len(text)
    return text[left:right].strip()


def contains_sufficient_direct_exclusion(text: str) -> bool:
    for pattern in SUFFICIENT_DIRECT_EXCLUSION_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            sentence = sentence_containing(text, match.start(), match.end())
            if not contains_negated_direct_exclusion(sentence):
                return True
    return False


def overclosure_without_direct_exclusion(text: str) -> bool:
    return contains_overclosure_operation(text) and not contains_sufficient_direct_exclusion(text)


def sentence_windows(text: str, window: int = 160) -> list[str]:
    sentences = [item.strip() for item in re.split(r"(?<=[.!?;:])\s+", text) if item.strip()]
    windows = set(sentences)
    for match in re.finditer(r"[^.!?;:]{0,%d}[.!?;:]?[^.!?;:]{0,%d}" % (window, window), text):
        chunk = match.group(0).strip()
        if chunk:
            windows.add(chunk)
    return list(windows)


def has_co_causation_language(claim: dict) -> bool:
    text = text_from(claim.get("statement", ""), claim.get("notes", ""), claim.get("direct_incompatibility_basis", ""))
    return any(term in text for term in CO_CAUSATION_TERMS)


def is_source_report_closure(claim: dict) -> bool:
    return claim.get("claim_kind") == "reported_claim" and claim.get("burden_profile") == "source_report"


def is_world_causal(claim: dict) -> bool:
    claim_type = claim.get("claim_type")
    claim_kind = claim.get("claim_kind", claim_type)
    return (claim_type in WORLD_CAUSAL_KINDS or claim_kind in WORLD_CAUSAL_KINDS) and not is_source_report_closure(claim)


GENERIC_CHAIN_WORDS = {
    "timeline",
    "timing",
    "mechanism",
    "effect",
    "scope",
    "provenance",
    "signal",
    "cause",
    "causal",
    "required",
    "requirement",
    "connects",
    "permits",
}


def link_markers(link: dict) -> list[str]:
    markers: list[str] = []
    link_id = link.get("id")
    if isinstance(link_id, str) and link_id.strip():
        markers.append(link_id.lower())
    for key in ("requirement", "notes"):
        value = link.get(key)
        if not isinstance(value, str):
            continue
        lowered = value.lower()
        words = [word for word in re.findall(r"[a-z0-9_-]{6,}", lowered) if word not in GENERIC_CHAIN_WORDS]
        markers.extend(words)
        if len(lowered) <= 80:
            markers.append(lowered)
    return list(dict.fromkeys(markers))


def marker_has_nearby_exclusion(text: str, marker: str, window: int = 160) -> bool:
    if not marker:
        return False
    marker_pattern = re.escape(marker)
    for match in re.finditer(marker_pattern, text, flags=re.IGNORECASE):
        start = max(0, match.start() - window)
        end = min(len(text), match.end() + window)
        nearby = text[start:end]
        if contains_sufficient_direct_exclusion(nearby):
            return True
    for sentence in sentence_windows(text, window=window):
        if re.search(marker_pattern, sentence, flags=re.IGNORECASE) and contains_sufficient_direct_exclusion(sentence):
            return True
    return False


def has_chain_link_exclusion(claim: dict, direct_relations: list[dict]) -> bool:
    chain = claim.get("required_chain")
    if not isinstance(chain, list) or not chain:
        return False
    basis_text = text_from(
        claim.get("direct_incompatibility_basis", ""),
        *(relation.get("incompatible_proposition", "") for relation in direct_relations),
        *(relation.get("explanation", "") for relation in direct_relations),
    )
    if not contains_sufficient_direct_exclusion(basis_text):
        return False
    for link in chain:
        if not isinstance(link, dict):
            continue
        if any(marker_has_nearby_exclusion(basis_text, marker) for marker in link_markers(link)):
            return True
    return False


def validate_case(case_dir: pathlib.Path) -> list[str]:
    errors: list[str] = []
    legacy_error = legacy_case_error(case_dir)
    if legacy_error:
        return [legacy_error]

    claims_data, load_errors = load_optional_object(case_dir / "claims.yml", "claims.yml")
    errors.extend(load_errors)
    if claims_data is None:
        return errors

    claims = [claim for claim in claims_data.get("claims", []) if isinstance(claim, dict)]
    claim_by_id = {claim.get("claim_id"): claim for claim in claims if claim.get("claim_id")}

    relations_data, load_errors = load_optional_object(case_dir / "evidence-relations.yml", "evidence-relations.yml")
    errors.extend(load_errors)
    relations_by_claim: dict[str, list[dict]] = defaultdict(list)
    if isinstance(relations_data, dict):
        for relation in relations_data.get("relations", []):
            if isinstance(relation, dict):
                relations_by_claim[relation.get("claim_ref")].append(relation)

    for claim_id, claim in claim_by_id.items():
        status = claim.get("status")
        direct_relations = [
            relation for relation in relations_by_claim.get(claim_id, [])
            if relation.get("relation_type") == DIRECT_CONTRADICTION
        ]

        if is_world_causal(claim) and claim.get("burden_profile") == "causal_chain" and status in STRONG_OR_NEGATIVE_STATUSES:
            chain = claim.get("required_chain")
            if not isinstance(chain, list) or not chain:
                errors.append(
                    f"causal_chain claim '{claim_id}' status='{status}' requires non-empty required_chain before strong or negative closure."
                )

        for relation in direct_relations:
            relation_text = text_from(
                relation.get("explanation", ""),
                relation.get("incompatible_proposition", ""),
            )
            if overclosure_without_direct_exclusion(relation_text):
                errors.append(
                    f"relation '{relation.get('relation_id', '?')}' uses contradicts_directly for claim '{claim_id}' but its basis is only stronger-alternative, missing-link, non-test, non-corroboration, method-gap, or absence language."
                )

        if status != "contradicted" or not is_world_causal(claim):
            continue

        claim_only_basis_text = text_from(
            claim.get("direct_incompatibility_basis", ""),
            claim.get("notes", ""),
        )
        direct_relation_basis_text = text_from(
            *(relation.get("explanation", "") for relation in direct_relations),
            *(relation.get("incompatible_proposition", "") for relation in direct_relations),
        )
        claim_basis_text = text_from(claim_only_basis_text, direct_relation_basis_text)
        if overclosure_without_direct_exclusion(claim_basis_text):
            errors.append(
                f"world-causal claim '{claim_id}' cannot be status='contradicted' when the direct-incompatibility basis is only a stronger alternative, missing link, non-test, non-corroboration, method gap, or absence operation."
            )

        if not contains_sufficient_direct_exclusion(claim_only_basis_text) and not contains_sufficient_direct_exclusion(direct_relation_basis_text):
            errors.append(
                f"world-causal claim '{claim_id}' status='contradicted' requires a non-negated direct exclusion in direct_incompatibility_basis or in a contradicts_directly relation basis."
            )

        if has_co_causation_language(claim) and not has_chain_link_exclusion(claim, direct_relations):
            errors.append(
                f"co-causation claim '{claim_id}' status='contradicted' must explicitly rule out an identified required_chain link; a stronger primary cause is insufficient."
            )

    errors.extend(validate_residual_path_closure(case_dir, claim_by_id))
    return errors


def claim_overlaps_investigation(claim: dict, investigation: dict, evidence_by_id: dict[str, dict]) -> bool:
    cluster_refs = {ref for ref in investigation.get("source_cluster_refs") or [] if isinstance(ref, str)}
    if not cluster_refs:
        return False
    claim_source_refs = {ref for ref in claim.get("source_refs") or [] if isinstance(ref, str)}
    if claim_source_refs & cluster_refs:
        return True
    for evidence_ref in claim.get("evidence_refs") or []:
        evidence = evidence_by_id.get(evidence_ref)
        if not isinstance(evidence, dict):
            continue
        if evidence.get("source_ref") in cluster_refs:
            return True
        evidence_source_refs = {ref for ref in evidence.get("source_refs") or [] if isinstance(ref, str)}
        if evidence_source_refs & cluster_refs:
            return True
    return False


def validate_residual_path_closure(case_dir: pathlib.Path, claim_by_id: dict[str, dict]) -> list[str]:
    errors: list[str] = []
    evidence_data, load_errors = load_optional_object(case_dir / "evidence-pack.yml", "evidence-pack.yml")
    errors.extend(load_errors)
    evidence_by_id = {}
    if isinstance(evidence_data, dict):
        evidence_by_id = {
            item.get("evidence_id"): item
            for item in evidence_data.get("evidence", [])
            if isinstance(item, dict) and item.get("evidence_id")
        }

    anomaly_data, load_errors = load_optional_object(case_dir / "anomaly-ledger.yml", "anomaly-ledger.yml")
    errors.extend(load_errors)
    if isinstance(anomaly_data, dict):
        for anomaly in anomaly_data.get("anomalies", []):
            if not isinstance(anomaly, dict):
                continue
            materiality = anomaly.get("materiality")
            if not isinstance(materiality, (int, float)) or materiality < HIGH_MATERIALITY_THRESHOLD:
                continue
            if anomaly.get("status") not in UNRESOLVED_STATUSES:
                continue
            affected_claims = anomaly.get("affected_claims") or []
            for claim_ref in affected_claims:
                claim = claim_by_id.get(claim_ref)
                if claim and claim.get("status") == "contradicted":
                    errors.append(
                        f"claim '{claim_ref}' is contradicted while high-materiality anomaly '{anomaly.get('anomaly_id', '?')}' remains {anomaly.get('status')}; residual-path-closure is required before negative closure (schema field pending)."
                    )

    integrity_data, load_errors = load_optional_object(case_dir / "investigation-integrity.yml", "investigation-integrity.yml")
    errors.extend(load_errors)
    if isinstance(integrity_data, dict):
        contradicted_claims = {
            claim_id: claim for claim_id, claim in claim_by_id.items()
            if claim.get("status") == "contradicted" and is_world_causal(claim)
        }
        for investigation in integrity_data.get("investigations", []):
            if not isinstance(investigation, dict):
                continue
            for path in investigation.get("non_tested_material_paths") or []:
                if not isinstance(path, dict):
                    continue
                materiality = path.get("materiality")
                quality = path.get("justification_quality", 1)
                low_quality = isinstance(quality, (int, float)) and quality < 0.7
                unresolved = path.get("justification_present") in {"partial", "no", "unknown"} or low_quality
                if not (isinstance(materiality, (int, float)) and materiality >= HIGH_MATERIALITY_THRESHOLD and unresolved):
                    continue
                # TODO: add affected_claims/residual_path_closure to non_tested_material_paths.
                # Until then, only block contradicted claims that overlap the investigation source cluster
                # through claim.source_refs or evidence.source_ref; unrelated causal claims in the same case are not blocked.
                for claim_ref, claim in contradicted_claims.items():
                    if not claim_overlaps_investigation(claim, investigation, evidence_by_id):
                        continue
                    errors.append(
                        f"claim '{claim_ref}' is contradicted while overlapping high-materiality non-tested path '{path.get('path_id', '?')}' remains unresolved/partial; residual-path-closure is required before negative closure (schema field pending; non-tested paths do not yet declare affected_claims)."
                    )
    return errors


def is_case_dir(path: pathlib.Path) -> bool:
    return any((path / marker).exists() for marker in CASE_MARKERS)


def discover_case_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    candidate_dirs = {root}
    for marker in CASE_MARKERS:
        candidate_dirs.update(path.parent for path in root.rglob(marker))
    return sorted(d for d in candidate_dirs if d.is_dir() and "_template" not in d.parts and is_case_dir(d))


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    case_dirs = discover_case_dirs(root)
    if not case_dirs:
        print(f"No overclosure case directories found under {root}")
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
        print(f"\n{total_errors} overclosure error(s) found.")
        return 1
    print("\nAll overclosure checks valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
