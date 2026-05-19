#!/usr/bin/env python3
"""Validate answer-receipt.yml against schema and semantic rules.

See docs/answer-receipt-discipline.md.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

import yaml
from jsonschema_compat import jsonschema

from case_compat import legacy_case_error

CASE_MARKERS = ("claims.yml", "evidence-relations.yml", "anomaly-ledger.yml", "investigation-integrity.yml")
SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "answer-receipt.v1.schema.json"

STRONG_STATUSES = {"strongly_supported", "established"}
WEAK_STATUSES = {"weak", "speculative", "unresolved", "no_verdict_possible"}
NON_FINAL_STATUSES = WEAK_STATUSES | {"plausible", "contradicted"}
WORLD_CLAIM_TYPES_REQUIRING_COUNTERHYPOTHESES = {
    "causal_claim", "motive_claim", "narrative_claim", "beneficiary_claim",
}

REPO_TASK_TYPES = {"repo_navigation", "repo_maintenance"}

ORACLE_DISCLAIMER_MARKERS = (
    "not a truth certificate",
    "kein wahrheitszertifikat",
    "evidence-structured judgment",
    "evidenzstrukturiertes urteil",
)

CONTROVERSY_REFUSAL_MARKERS = (
    "controversial",
    "controversy",
    "politically sensitive",
    "kontrovers",
    "politisch sensibel",
    "umstritten",
    "heikles thema",
)


def safe_load_yaml(path: pathlib.Path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except Exception as exc:
        return None, str(exc)


def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def schema_validate(receipt: dict, schema: dict) -> list[str]:
    errors: list[str] = []
    validator = jsonschema.Draft7Validator(schema)
    for error in validator.iter_errors(receipt):
        errors.append(f"schema: {list(error.absolute_path)}: {error.message}")
    return errors


def semantic_checks(receipt: dict) -> list[str]:
    errors: list[str] = []

    task = receipt.get("task_classification", "")
    verdicts = receipt.get("verdicts_used", []) or []
    counter = receipt.get("counterhypotheses_considered", []) or []
    forbidden_check = receipt.get("forbidden_upgrades_check", {}) or {}
    self_scan = receipt.get("banned_phrases_self_scan", {}) or {}
    refusal_check = receipt.get("refusal_check", {}) or {}
    external = receipt.get("external_research", {}) or {}
    answer_summary = receipt.get("answer_summary", "") or ""
    final_unc = receipt.get("final_uncertainty_statement", "") or ""
    oracle = receipt.get("oracle_disclaimer_present", False)
    what_change = receipt.get("what_would_change_assessment", "") or ""

    # 1. Banned-phrases consistency: self-scan must be honest.
    # (Note: validate_forbidden_language.py runs the deep regex scan.
    # Here we just check that scanned=true and hits is an array.)
    if not self_scan.get("scanned", False):
        errors.append("banned_phrases_self_scan.scanned must be true")
    if not isinstance(self_scan.get("hits", []), list):
        errors.append("banned_phrases_self_scan.hits must be a list")

    # 2. Counterhypothesis floor for strong verdicts on causal/motive claims.
    needs_counterhypotheses = False
    for v in verdicts:
        if not isinstance(v, dict):
            continue
        status = v.get("status")
        statement = (v.get("statement") or "").lower()
        if status not in STRONG_STATUSES:
            continue
        # We don't know claim_type from receipt; detect causal/motive keywords as proxy
        looks_causal = any(kw in statement for kw in (
            "caused", "verursachte", "led to", "führte zu", "fuhrte zu",
            "because of", "weil", "motivated", "motiviert",
        ))
        if looks_causal:
            needs_counterhypotheses = True
    if needs_counterhypotheses:
        strong_counter = [
            c for c in counter
            if isinstance(c, dict) and isinstance(c.get("steelman_quality"), (int, float))
            and c["steelman_quality"] >= 0.5
        ]
        if not strong_counter:
            errors.append(
                "verdicts include strongly_supported/established on a causal/motive-like statement, "
                "but counterhypotheses_considered has no entry with steelman_quality >= 0.5"
            )

    # 3. Refusal-as-neutrality semantics
    refused = refusal_check.get("refused", False)
    refusal_type = refusal_check.get("refusal_type")
    if refused:
        valid_types = {"out_of_scope", "missing_tools", "missing_evidence", "capability"}
        if refusal_type not in valid_types:
            errors.append(
                f"refusal_check.refused=true but refusal_type='{refusal_type}' is not one of {sorted(valid_types)}"
            )
        # If refusal_type is missing_evidence, require at least one no_verdict_possible/unresolved verdict
        if refusal_type == "missing_evidence":
            has_unresolved = any(
                isinstance(v, dict) and v.get("status") in {"no_verdict_possible", "unresolved"}
                for v in verdicts
            )
            if not has_unresolved:
                errors.append(
                    "refusal_type=missing_evidence requires at least one verdict with status no_verdict_possible or unresolved"
                )
        # Refusal cannot cite controversy/sensitivity as reason
        combined_unc = (final_unc + " " + refusal_check.get("notes", "")).lower()
        for marker in CONTROVERSY_REFUSAL_MARKERS:
            if marker in combined_unc:
                errors.append(
                    f"refusal_check cites '{marker}' as reason; controversy/sensitivity is not a valid refusal reason (see docs/refusal-discipline.md)"
                )

    # 4. External-research declaration for non-repo tasks
    if task not in REPO_TASK_TYPES:
        tools = external.get("tools_used") or []
        bg_only = external.get("background_knowledge_only", False)
        if not tools and not bg_only:
            errors.append(
                f"task_classification={task}: external_research.tools_used is empty and "
                "background_knowledge_only is not set; declare one or the other"
            )
        if not tools and bg_only:
            # require the final_uncertainty_statement to flag background-only
            if not re.search(
                r"background[-\s]?knowledge[-\s]?only|hintergrundwissen[-\s]?nur|no external verification|keine externe verifikation",
                final_unc,
                re.IGNORECASE,
            ):
                errors.append(
                    "external_research.background_knowledge_only=true but final_uncertainty_statement does not "
                    "explicitly label the answer as background-knowledge-only / no external verification"
                )

    # 5. Source-cluster independence for strong verdicts
    has_strong = any(
        isinstance(v, dict) and v.get("status") in STRONG_STATUSES for v in verdicts
    )
    sc_audit = receipt.get("source_cluster_audit", {}) or {}
    if has_strong:
        indep = sc_audit.get("independence_verified", False)
        fragility = sc_audit.get("fragility_score")
        if not indep and not (isinstance(fragility, (int, float)) and fragility >= 0.7):
            errors.append(
                "at least one verdict is strongly_supported/established but source_cluster_audit "
                "neither verifies independence nor documents fragility_score >= 0.7"
            )

    # 6. Oracle disclaimer
    if not oracle:
        errors.append("oracle_disclaimer_present must be true")
    else:
        combined = (answer_summary + " " + final_unc).lower()
        if not any(marker in combined for marker in ORACLE_DISCLAIMER_MARKERS):
            errors.append(
                "oracle_disclaimer_present=true but neither answer_summary nor "
                "final_uncertainty_statement contains the disclaimer phrase "
                "('not a truth certificate' / 'kein Wahrheitszertifikat')"
            )

    # 7. what_would_change_assessment required for non-established verdicts
    has_non_established = any(
        isinstance(v, dict) and v.get("status") in NON_FINAL_STATUSES for v in verdicts
    )
    if has_non_established and not what_change.strip():
        errors.append(
            "verdicts include non-established statuses; what_would_change_assessment must be non-empty"
        )

    # 8. forbidden_upgrades_check: at least one upgrade considered if any verdict is strong
    if has_strong:
        considered = forbidden_check.get("upgrades_considered") or []
        if not considered:
            errors.append(
                "verdicts include strongly_supported/established but "
                "forbidden_upgrades_check.upgrades_considered is empty; "
                "every strong verdict requires explicit consideration of which upgrades were avoided"
            )

    return errors


def validate_receipt_file(receipt_path: pathlib.Path, schema: dict) -> list[str]:
    if not receipt_path.exists():
        return []
    data, err = safe_load_yaml(receipt_path)
    if err:
        return [f"could not parse {receipt_path}: {err}"]
    if not isinstance(data, dict):
        return [f"{receipt_path}: must be a YAML object"]

    errors = schema_validate(data, schema)
    if errors:
        return errors
    errors.extend(semantic_checks(data))
    return errors


def validate_case(case_dir: pathlib.Path, schema: dict) -> list[str]:
    errors: list[str] = []
    legacy_error = legacy_case_error(case_dir)
    if legacy_error:
        return [legacy_error]

    receipt_paths = list(case_dir.glob("answer-receipt.yml"))
    answers_dir = case_dir / "answers"
    if answers_dir.is_dir():
        receipt_paths.extend(sorted(answers_dir.glob("*answer-receipt*.yml")))
        receipt_paths.extend(sorted(answers_dir.glob("*.receipt.yml")))

    for path in receipt_paths:
        rel = path.relative_to(case_dir)
        for err in validate_receipt_file(path, schema):
            errors.append(f"{rel}: {err}")

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
        print(f"No case directories found under {root}")
        return 0

    schema = load_schema()
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
        print(f"\n{total_errors} answer-receipt error(s) found.")
        return 1
    print("\nAll answer-receipt checks valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
