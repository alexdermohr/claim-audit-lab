#!/usr/bin/env python3
"""Derive bias signals from case artifacts.

Bias signals are generated, not confessed. Each signal is an explanation-bearing
observation about a case artifact pattern; it is not proof of distortion. See
docs/bias-signal-discipline.md.

Usage:
    python scripts/generate_bias_signals.py cases
    python scripts/generate_bias_signals.py cases --write
    python scripts/generate_bias_signals.py cases --check
    python scripts/generate_bias_signals.py cases --case cases/critical-inquiry/example
    python scripts/generate_bias_signals.py cases --format json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any

import yaml

from case_compat import find_cases_root
from jsonschema_compat import jsonschema

GENERATED_BY = "scripts/generate_bias_signals.py"
GENERATED_SUBDIR = "_generated"
GENERATED_FILENAME = "bias-signals.yml"
SIGNALS_SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "bias-signals.v1.schema.json"

WEAK_STATUSES = {"weak", "speculative", "unresolved", "no_verdict_possible"}
STRONG_STATUSES = {"strongly_supported", "established"}
COUNTER_REQUIRING_TYPES = {"causal_claim", "motive_claim"}

# Strong-effect relation types, kept in sync with STRONG_EFFECT_RELATIONS in
# validate_reported_claim_world_effect.py. The bare forms "supports",
# "contradicts", and "contradicts_indirectly" are legacy aliases not present in
# evidence-relation.v1.schema.json's enum; they are recognised here so a relation
# cannot dodge the gate by relabelling to a non-canonical type.
DIRECTIONAL_RELATION_TYPES = {
    "supports",  # legacy alias (not in schema enum)
    "supports_directly",
    "supports_indirectly",
    "weakens",
    "undercuts",
    "contradicts",  # legacy alias (not in schema enum)
    "contradicts_directly",
    "contradicts_conditionally",
    "contradicts_indirectly",  # legacy alias (not in schema enum)
    "alternative_explanation",
    "method_challenge",
}
THRESHOLD_GATES = (0.60, 0.75)
THRESHOLD_WINDOW = 0.03

PENDING_REDTEAM_VERDICTS = {"pending", "pending_independent_review"}
FINAL_LANGUAGE_TOKENS = {"assessed", "final_under_uncertainty"}

# Finalizing prose: stronger than any below-established verdict warrants.
FINALIZING_PATTERNS = (
    r"\bproves\b",
    r"\bproven\b",
    r"\bestablishes\b",
    r"\bclearly\s+shows\b",
    r"\bdemonstrates\s+conclusively\b",
    r"\bconclusively\b",
    r"\bdefinitively\b",
    r"\bbeweist\b",
    r"\bwiderlegt\b",
    r"\bbelegt\s+eindeutig\b",
    r"\beindeutig\s+belegt\b",
    r"\bist\s+damit\s+erwiesen\b",
    r"\berwiesenerma[ßs]en\b",
)

# Framing tokens that a comparative claim must declare to be adequately framed.
COMPARATIVE_FRAMING_TOKENS = (
    "base rate",
    "base_rate",
    "baseline",
    "basisrate",
    "null hypothesis",
    "null_hypothesis",
    "nullhypothese",
    "alternative",
    "alternativen",
    "comparison base",
    "comparison_base",
    "comparative_base_rate",
    "vergleichsbasis",
    "reference class",
    "referenzklasse",
    "prior",
    "decision rule",
    "decision_rule",
    "decision logic",
    "entscheidungslogik",
    "evaluation standard",
    "bewertungsma[ßs]stab",
)

WHAT_WOULD_CHANGE_PATTERNS = (
    r"what\s+would\s+change",
    r"what_would_change",
    r"was\s+(?:das\s+urteil|die\s+einsch[äa]tzung|den\s+verdict)[^.]{0,40}\b[äa]nder",
)


def _load_yaml(path: pathlib.Path) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def relative_case_ref(case_dir: pathlib.Path) -> str:
    root = find_cases_root(case_dir)
    if root is not None:
        rel = case_dir.relative_to(root).as_posix()
        return f"cases/{rel}" if rel != "." else "cases"
    return case_dir.as_posix()


def _signal_id(case_ref: str, signal_type: str, affected_refs: list[str], observation: str) -> str:
    payload = "|".join(
        [case_ref, signal_type, ",".join(sorted(affected_refs)), observation]
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"bs_{digest[:12]}"


class CaseContext:
    def __init__(self, case_dir: pathlib.Path):
        self.case_dir = case_dir
        self.case_ref = relative_case_ref(case_dir)
        claims_doc = _load_yaml(case_dir / "claims.yml")
        self.claims = _as_list(claims_doc, "claims")
        relations_doc = _load_yaml(case_dir / "evidence-relations.yml")
        self.relations = _as_list(relations_doc, "relations")
        sources_doc = _load_yaml(case_dir / "sources.yml")
        self.sources = _as_list(sources_doc, "sources")
        swa_doc = _load_yaml(case_dir / "source-weight-audit.yml")
        self.source_audit = _as_list(swa_doc, "records")
        self.redteam = _load_yaml(case_dir / "redteam.yml")
        self.lifecycle = _load_yaml(case_dir / "lifecycle.yml")
        self.assessment_text = _read_text(case_dir / "assessment.md")
        self.has_argument_provenance = (case_dir / "argument-provenance.yml").exists()
        self.has_hypotheses = (case_dir / "hypotheses.yml").exists()
        evidence_pack_doc = _load_yaml(case_dir / "evidence-pack.yml")
        self.evidence_pack = _as_list(evidence_pack_doc, "evidence")


def _as_list(doc: Any, key: str) -> list[dict]:
    if isinstance(doc, dict) and isinstance(doc.get(key), list):
        return [item for item in doc[key] if isinstance(item, dict)]
    return []


def _read_text(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _eligible_lines(text: str) -> list[str]:
    """Lines outside markdown tables, blockquotes, and steelman fences."""
    lines: list[str] = []
    in_steelman = False
    for raw in text.splitlines():
        stripped = raw.lstrip()
        if stripped.startswith("```"):
            if "steelman" in stripped.lower():
                in_steelman = True
            elif in_steelman:
                in_steelman = False
            continue
        if in_steelman:
            continue
        if stripped.startswith("|") or stripped.startswith(">"):
            continue
        lines.append(raw)
    return lines


def _get_evidence_refs_from_relation(relation: dict) -> list[str]:
    """Collect all evidence refs from a relation (singular and plural fields)."""
    refs: list[str] = []
    singular = relation.get("evidence_ref")
    if isinstance(singular, str) and singular:
        refs.append(singular)
    plural = relation.get("evidence_refs") or []
    if isinstance(plural, list):
        refs.extend(r for r in plural if isinstance(r, str) and r)
    return list(dict.fromkeys(refs))


def _load_signals_schema() -> dict | None:
    try:
        with open(SIGNALS_SCHEMA_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _schema_errors_for_document(document: dict, schema: dict) -> list[str]:
    validator = jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())
    return [
        f"Schema error at {list(e.absolute_path)}: {e.message}"
        for e in sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path))
    ]


def _assessment_status_token(text: str) -> str:
    for line in text.splitlines()[:20]:
        m = re.search(r"status[:\*\s]+([a-z_]+)", line, flags=re.IGNORECASE)
        if m:
            return m.group(1).lower()
    return ""


# --- detectors ---------------------------------------------------------------


def detect_assessment_verdict_mismatch(ctx: CaseContext) -> list[dict]:
    signals: list[dict] = []
    if not ctx.assessment_text:
        return signals
    lines = _eligible_lines(ctx.assessment_text)
    for claim in ctx.claims:
        claim_id = claim.get("claim_id")
        status = claim.get("status", "")
        if not claim_id or status not in WEAK_STATUSES:
            continue
        matched: str | None = None
        for line in lines:
            if claim_id not in line:
                continue
            for pattern in FINALIZING_PATTERNS:
                m = re.search(pattern, line, flags=re.IGNORECASE)
                if m:
                    matched = m.group(0).lower()
                    break
            if matched:
                break
        if not matched:
            continue
        observation = (
            f"assessment.md uses finalizing language '{matched}' about claim "
            f"{claim_id} whose structured status is '{status}'."
        )
        signals.append(
            _build(
                ctx,
                signal_type="assessment_verdict_mismatch",
                severity=0.82,
                affected_claims=[claim_id],
                detected_from=["assessment.md", f"claims.yml#{claim_id}"],
                observation=observation,
            )
        )
    return signals


def detect_relation_threshold_proximity(ctx: CaseContext) -> list[dict]:
    signals: list[dict] = []
    for relation in ctx.relations:
        rtype = relation.get("relation_type", "")
        strength = relation.get("strength")
        relation_id = relation.get("relation_id")
        claim_ref = relation.get("claim_ref")
        if rtype not in DIRECTIONAL_RELATION_TYPES:
            continue
        if not isinstance(strength, (int, float)) or isinstance(strength, bool):
            continue
        near = next(
            (gate for gate in THRESHOLD_GATES if abs(strength - gate) <= THRESHOLD_WINDOW + 1e-9),
            None,
        )
        if near is None or not relation_id:
            continue
        observation = (
            f"relation {relation_id} ({rtype}) strength {strength} sits within "
            f"±{THRESHOLD_WINDOW} of gate {near}; a small numeric move crosses a verdict gate."
        )
        affected = [claim_ref] if isinstance(claim_ref, str) and claim_ref else []
        signals.append(
            _build(
                ctx,
                signal_type="relation_threshold_proximity",
                severity=0.50,
                affected_claims=affected,
                detected_from=[f"evidence-relations.yml#{relation_id}"],
                observation=observation,
            )
        )
    return signals


def _composite_trust(source_weight: dict) -> float | None:
    positive = ("primary_proximity", "method_transparency", "reproducibility",
                "source_cluster_independence", "historical_track_record")
    risk = ("institutional_interest_risk", "update_latency_risk")
    values: list[float] = []
    for key in positive:
        v = source_weight.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            values.append(float(v))
    for key in risk:
        v = source_weight.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            values.append(1.0 - float(v))
    if len(values) < 5:
        return None
    return sum(values) / len(values)


def detect_source_weight_asymmetry(ctx: CaseContext) -> list[dict]:
    signals: list[dict] = []
    composites: dict[str, float] = {}
    for source in ctx.sources:
        sid = source.get("source_id")
        weight = source.get("source_weight")
        if not isinstance(sid, str) or not isinstance(weight, dict):
            continue
        comp = _composite_trust(weight)
        if comp is not None:
            composites[sid] = comp
    if len(composites) < 2:
        return signals
    values = list(composites.values())
    spread = max(values) - min(values)
    if spread < 0.4:
        return signals
    mean = sum(values) / len(values)

    audit_notes: dict[str, str] = {}
    for record in ctx.source_audit:
        ref = record.get("source_ref")
        if isinstance(ref, str):
            audit_notes[ref] = str(record.get("notes", "") or "")

    claims_by_source: dict[str, list[str]] = {}
    for claim in ctx.claims:
        cid = claim.get("claim_id")
        if not isinstance(cid, str):
            continue
        for ref in claim.get("source_refs", []) or []:
            if isinstance(ref, str):
                claims_by_source.setdefault(ref, []).append(cid)

    for sid, comp in sorted(composites.items()):
        if abs(comp - mean) < 0.25:
            continue
        justified = len(audit_notes.get(sid, "").strip()) >= 40
        if justified:
            continue
        direction = "above" if comp > mean else "below"
        observation = (
            f"source {sid} composite trust {round(comp, 3)} is far {direction} the case "
            f"mean {round(mean, 3)} (spread {round(spread, 3)}) without a justification in "
            f"source-weight-audit.yml."
        )
        signals.append(
            _build(
                ctx,
                signal_type="source_weight_asymmetry",
                severity=0.60,
                affected_claims=sorted(set(claims_by_source.get(sid, []))),
                detected_from=[f"sources.yml#{sid}", "source-weight-audit.yml"],
                observation=observation,
            )
        )
    return signals


def detect_reported_claim_world_pressure(ctx: CaseContext) -> list[dict]:
    signals: list[dict] = []

    # Build a set of reported_claim / source_report claim IDs.
    reported_claim_ids: set[str] = set()
    for claim in ctx.claims:
        cid = claim.get("claim_id")
        if isinstance(cid, str) and (
            claim.get("claim_kind") == "reported_claim"
            or claim.get("burden_profile") == "source_report"
        ):
            reported_claim_ids.add(cid)

    # Path A: world_claim_refs or assessment mention on the claim itself.
    for claim in ctx.claims:
        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or claim_id not in reported_claim_ids:
            continue
        world_refs = [r for r in (claim.get("world_claim_refs") or []) if isinstance(r, str)]
        mentioned = bool(ctx.assessment_text) and claim_id in ctx.assessment_text
        pressure = bool(world_refs) or mentioned
        if not pressure or ctx.has_argument_provenance:
            continue
        trigger = "world_claim_refs" if world_refs else "assessment mention"
        observation = (
            f"reported_claim {claim_id} is leveraged toward a world claim (via {trigger}) "
            f"while argument-provenance.yml is missing; the inference path is undeclared."
        )
        signals.append(
            _build(
                ctx,
                signal_type="reported_claim_world_pressure",
                severity=0.78,
                affected_claims=sorted(set([claim_id, *world_refs])),
                detected_from=[f"claims.yml#{claim_id}", "argument-provenance.yml(missing)"],
                observation=observation,
            )
        )

    # Path B: evidence-pack items derived from reported claims used via directional relations.
    if not ctx.has_argument_provenance and reported_claim_ids and ctx.evidence_pack:
        # Map evidence_id → list of reported claim IDs it is derived from.
        reported_evidence: dict[str, list[str]] = {}
        for evidence in ctx.evidence_pack:
            eid = evidence.get("evidence_id")
            if not isinstance(eid, str):
                continue
            linked = [
                ref for ref in (evidence.get("claim_refs") or [])
                if isinstance(ref, str) and ref in reported_claim_ids
            ]
            if linked:
                reported_evidence[eid] = linked

        if reported_evidence:
            for relation in ctx.relations:
                rtype = relation.get("relation_type", "")
                if rtype not in DIRECTIONAL_RELATION_TYPES:
                    continue
                ev_refs = _get_evidence_refs_from_relation(relation)
                triggering_ev_refs: list[str] = []
                involved_reported: set[str] = set()
                for ev_ref in ev_refs:
                    if ev_ref in reported_evidence:
                        triggering_ev_refs.append(ev_ref)
                        involved_reported.update(reported_evidence[ev_ref])
                if not involved_reported:
                    continue
                target_claim = relation.get("claim_ref")
                if not isinstance(target_claim, str) or not target_claim:
                    continue
                relation_id = relation.get("relation_id", "?")
                observation = (
                    f"evidence {sorted(triggering_ev_refs)} derived from reported_claim(s) "
                    f"{sorted(involved_reported)} is used via '{rtype}' relation "
                    f"({relation_id}) toward claim {target_claim} while "
                    f"argument-provenance.yml is missing; the inference path is undeclared."
                )
                signals.append(
                    _build(
                        ctx,
                        signal_type="reported_claim_world_pressure",
                        severity=0.78,
                        affected_claims=sorted(involved_reported | {target_claim}),
                        detected_from=[
                            f"evidence-relations.yml#{relation_id}",
                            "argument-provenance.yml(missing)",
                        ],
                        observation=observation,
                    )
                )

    return signals


def detect_comparative_claim_underframed(ctx: CaseContext) -> list[dict]:
    signals: list[dict] = []
    for claim in ctx.claims:
        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str):
            continue
        is_comparative = (
            claim.get("claim_kind") == "comparative_claim"
            or claim.get("claim_type") == "comparative_claim"
            or claim.get("burden_profile") == "comparative"
        )
        if not is_comparative:
            continue
        haystack_parts: list[str] = [str(claim.get("notes", "") or "")]
        for item in claim.get("requires", []) or []:
            haystack_parts.append(str(item))
        for item in claim.get("counterclaims", []) or []:
            haystack_parts.append(str(item))
        haystack = " ".join(haystack_parts).lower()
        framed = any(re.search(token, haystack) for token in COMPARATIVE_FRAMING_TOKENS)
        if framed:
            continue
        observation = (
            f"comparative claim {claim_id} declares no base rate, null hypothesis, "
            f"explicit alternative, or decision standard in requires/notes/counterclaims."
        )
        signals.append(
            _build(
                ctx,
                signal_type="comparative_claim_underframed",
                severity=0.60,
                affected_claims=[claim_id],
                detected_from=[f"claims.yml#{claim_id}"],
                observation=observation,
            )
        )
    return signals


def detect_redteam_pending_with_final_language(ctx: CaseContext) -> list[dict]:
    if not isinstance(ctx.redteam, dict):
        return []
    verdict = ""
    if isinstance(ctx.redteam.get("verdict"), dict):
        verdict = str(ctx.redteam["verdict"].get("status", ""))
    if verdict not in PENDING_REDTEAM_VERDICTS:
        return []
    lifecycle_status = ""
    if isinstance(ctx.lifecycle, dict):
        lifecycle_status = str(ctx.lifecycle.get("status", ""))
    assessment_status = _assessment_status_token(ctx.assessment_text)
    final_language = (
        lifecycle_status in FINAL_LANGUAGE_TOKENS
        or assessment_status in FINAL_LANGUAGE_TOKENS
    )
    if not final_language:
        return []
    observation = (
        f"red-team verdict is '{verdict}' while finalizing language is present "
        f"(lifecycle status '{lifecycle_status or 'n/a'}', assessment status "
        f"'{assessment_status or 'n/a'}')."
    )
    return [
        _build(
            ctx,
            signal_type="redteam_pending_with_final_language",
            severity=0.85,
            affected_claims=[],
            detected_from=["redteam.yml", "lifecycle.yml"],
            observation=observation,
        )
    ]


def detect_counterhypothesis_understeelman(ctx: CaseContext) -> list[dict]:
    # Case-global prose quality of the steelman (assessment.md is not structured
    # per-claim, so these prose checks are evaluated once and reused per claim).
    steelman_present = "```steelman" in ctx.assessment_text
    what_would_change = any(
        re.search(p, ctx.assessment_text, flags=re.IGNORECASE) for p in WHAT_WOULD_CHANGE_PATTERNS
    )
    low_quality = False
    for m in re.finditer(r"steelman[^0-9]{0,40}(0?\.\d+)", ctx.assessment_text, flags=re.IGNORECASE):
        try:
            if float(m.group(1)) < 0.3:
                low_quality = True
                break
        except ValueError:  # pragma: no cover - defensive
            continue
    understeelman = (not steelman_present) or (not what_would_change) or low_quality
    if not understeelman:
        return []
    reason = (
        "no steelman block" if not steelman_present
        else "steelman quality below 0.3" if low_quality
        else "no 'what would change the verdict' statement"
    )

    signals: list[dict] = []
    for claim in ctx.claims:
        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str):
            continue
        if claim.get("status") not in STRONG_STATUSES:
            continue
        if claim.get("claim_type") not in COUNTER_REQUIRING_TYPES:
            continue
        # Claim-local: only fire if THIS claim actually carries a counterhypothesis.
        # A bare steelman block elsewhere is not attributable to this claim, so the
        # claim's own counterclaims (or a case-level hypotheses ledger) are required.
        has_counter = bool(claim.get("counterclaims") or []) or ctx.has_hypotheses
        if not has_counter:
            continue
        observation = (
            f"strong causal/motive claim {claim_id} carries a counterhypothesis "
            f"but the steelman is under-developed ({reason})."
        )
        signals.append(
            _build(
                ctx,
                signal_type="counterhypothesis_understeelman",
                severity=0.70,
                affected_claims=[claim_id],
                detected_from=[f"claims.yml#{claim_id}", "assessment.md"],
                observation=observation,
            )
        )
    return signals


DETECTORS = (
    detect_assessment_verdict_mismatch,
    detect_relation_threshold_proximity,
    detect_source_weight_asymmetry,
    detect_reported_claim_world_pressure,
    detect_comparative_claim_underframed,
    detect_redteam_pending_with_final_language,
    detect_counterhypothesis_understeelman,
)


def _build(
    ctx: CaseContext,
    *,
    signal_type: str,
    severity: float,
    affected_claims: list[str],
    detected_from: list[str],
    observation: str,
) -> dict:
    affected_refs = [*affected_claims, *detected_from]
    signal_id = _signal_id(ctx.case_ref, signal_type, affected_refs, observation)
    return {
        "signal_id": signal_id,
        "signal_type": signal_type,
        "severity": severity,
        "affected_claims": affected_claims,
        "detected_from": detected_from,
        "observation": observation,
        "required_response": True,
    }


def generate_for_case(case_dir: pathlib.Path) -> list[dict]:
    ctx = CaseContext(case_dir)
    signals: list[dict] = []
    for detector in DETECTORS:
        signals.extend(detector(ctx))
    signals.sort(key=lambda s: (s["signal_type"], s["signal_id"]))
    return signals


def build_document(case_ref: str, signals: list[dict]) -> dict:
    return {
        "schema_version": "1.0",
        "case_ref": case_ref,
        "generated_by": GENERATED_BY,
        "signals": signals,
    }


def discover_case_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted(
        {
            marker.parent
            for marker in root.rglob("claims.yml")
            if "_template" not in marker.parts and GENERATED_SUBDIR not in marker.parts
        }
    )


def _generated_path(case_dir: pathlib.Path) -> pathlib.Path:
    return case_dir / GENERATED_SUBDIR / GENERATED_FILENAME


def _write_document(case_dir: pathlib.Path, document: dict) -> pathlib.Path:
    out_path = _generated_path(case_dir)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(document, f, sort_keys=False, allow_unicode=True)
    return out_path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Derive bias signals from case artifacts.")
    parser.add_argument("cases_dir")
    parser.add_argument("--write", action="store_true", help="write _generated/bias-signals.yml per case")
    parser.add_argument("--check", action="store_true", help="fail if a committed generated file is stale")
    parser.add_argument("--case", help="limit to a single case directory")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    root = pathlib.Path(args.cases_dir)
    if args.case:
        case_dirs = [pathlib.Path(args.case)]
    else:
        if not root.is_dir():
            print(f"ERROR: {root} is not a directory", file=sys.stderr)
            return 1
        case_dirs = discover_case_dirs(root)

    if not case_dirs:
        print(f"No case directories found under {root}")
        return 0

    signals_schema = _load_signals_schema()

    json_payload: list[dict] = []
    drift = 0
    for case_dir in case_dirs:
        signals = generate_for_case(case_dir)
        document = build_document(relative_case_ref(case_dir), signals)

        if signals_schema:
            schema_errs = _schema_errors_for_document(document, signals_schema)
            if schema_errs:
                for err in schema_errs:
                    print(f"SCHEMA ERROR {case_dir}: {err}", file=sys.stderr)
                return 1

        if args.check:
            committed = _generated_path(case_dir)
            if committed.exists():
                existing = _load_yaml(committed)
                existing_signals = existing.get("signals") if isinstance(existing, dict) else None
                if existing_signals != signals:
                    print(f"DRIFT {committed}: committed signals are stale; re-run with --write.")
                    drift += 1
                else:
                    print(f"OK    {committed}")
            else:
                print(f"OK    {case_dir} (no committed signals; generated in memory)")
            continue

        if args.write:
            out_path = _write_document(case_dir, document)
            print(f"WROTE {out_path} ({len(signals)} signal(s))")
            continue

        if args.format == "json":
            json_payload.append(document)
        else:
            print(f"{document['case_ref']}: {len(signals)} signal(s)")
            for signal in signals:
                print(
                    f"  [{signal['signal_type']}] {signal['signal_id']} "
                    f"severity={signal['severity']} affects={signal['affected_claims']}"
                )
                print(f"    {signal['observation']}")

    if args.check:
        if drift:
            print(f"\n{drift} stale generated file(s).")
            return 1
        print("\nAll committed bias-signal files current.")
        return 0

    if args.format == "json" and not args.write:
        print(json.dumps(json_payload, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
