#!/usr/bin/env python3
"""Block refusal-as-neutrality in answer-receipt artifacts.

Checks answer-receipt.yml files for refusal patterns that present
themselves as balance or neutrality without structured declaration per
docs/refusal-discipline.md.
"""

from __future__ import annotations

import pathlib
import re
import sys

import yaml

from case_compat import legacy_case_error

CASE_MARKERS = ("claims.yml", "evidence-relations.yml", "anomaly-ledger.yml", "investigation-integrity.yml")

# Phrases that indicate refusal-as-neutrality (Category E in forbidden-language.md)
COVERT_REFUSAL_PATTERNS = (
    r"\bi\s+(?:cannot|can[' ]?t|won[' ]?t)\s+(?:evaluate|assess|judge)\b",
    r"\bthis\s+is\s+a\s+sensitive\s+topic\b",
    r"\bnot\s+appropriate\s+to\s+assess\b",
    r"\bboth\s+sides\s+have\s+valid\s+points\b",
    r"\breasonable\s+people\s+disagree\b",
    r"\bi\s+don[' ]?t\s+want\s+to\s+take\s+a\s+side\b",
    r"\bkann\s+ich\s+nicht\s+bewerten\b",
    r"\bein\s+sensibles\s+thema,?\s+daher\b",
    r"\bes\s+w[aä]re\s+unangemessen,?\s+dies\s+zu\s+beurteilen\b",
    r"\bbeide\s+seiten\s+haben\s+gute\s+argumente\b",
    r"\bzu\s+politisch,?\s+um\s+sie\s+zu\s+beantworten\b",
    r"\bich\s+m[oö]chte\s+(?:hier\s+)?kein\s+urteil\s+abgeben\b",
)

# Phrases that signal balanced framing
BALANCED_FRAMING_PATTERNS = (
    r"\bboth\s+sides\b",
    r"\bon\s+the\s+one\s+hand.*\bon\s+the\s+other\s+hand\b",
    r"\beinerseits.*andererseits\b",
    r"\bbeide\s+seiten\b",
)

CONTROVERSY_REASONS = (
    "controversial", "controversy", "politically sensitive",
    "kontrovers", "politisch sensibel", "umstritten", "heikles thema",
    "political", "politisch",
)

REPO_TASK_TYPES = {"repo_navigation", "repo_maintenance"}


def safe_load_yaml(path: pathlib.Path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except Exception as exc:
        return None, str(exc)


def scan_text_for_covert_refusal(text: str) -> list[str]:
    hits: list[str] = []
    lowered = text.lower()
    for pattern in COVERT_REFUSAL_PATTERNS:
        for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
            hits.append(match.group(0))
    return hits


def check_receipt(receipt: dict) -> list[str]:
    errors: list[str] = []
    task = receipt.get("task_classification", "")
    refusal_check = receipt.get("refusal_check", {}) or {}
    refused = refusal_check.get("refused", False)
    refusal_type = refusal_check.get("refusal_type")
    answer_summary = receipt.get("answer_summary", "") or ""
    final_unc = receipt.get("final_uncertainty_statement", "") or ""
    refusal_notes = refusal_check.get("notes", "") or ""
    external = receipt.get("external_research", {}) or {}

    # Rule 1: covert refusal phrase in answer_summary but refused=false
    covert_hits = scan_text_for_covert_refusal(answer_summary)
    if covert_hits and not refused:
        errors.append(
            f"answer_summary contains covert refusal phrase(s) {covert_hits} but refusal_check.refused=false; "
            f"refusal must be declared explicitly per docs/refusal-discipline.md"
        )

    # Rule 2: refusal_type, when present, must be valid.
    valid_types = {"out_of_scope", "missing_tools", "missing_evidence", "capability"}
    if refusal_type is not None and refusal_type not in valid_types:
        errors.append(
            f"refusal_check.refusal_type='{refusal_type}' is invalid; "
            f"must be one of {sorted(valid_types)}"
        )
    if refused and refusal_type is None:
        errors.append(
            "refusal_check.refused=true requires refusal_check.refusal_type to be set"
        )

    # Rule 3: declared refusal types must match refused semantics from policy.
    if refusal_type in {"missing_tools", "missing_evidence"} and refused:
        errors.append(
            f"refusal_type={refusal_type} requires refusal_check.refused=false "
            "(tool-limited/non-verdict path, not refusal)"
        )
    if refusal_type in {"out_of_scope", "capability"} and not refused:
        errors.append(
            f"refusal_type={refusal_type} requires refusal_check.refused=true"
        )

    # Rule 4: missing_evidence requires unresolved/no_verdict_possible verdict(s).
    if refusal_type == "missing_evidence":
        verdicts = receipt.get("verdicts_used", []) or []
        has_unresolved = any(
            isinstance(v, dict) and v.get("status") in {"no_verdict_possible", "unresolved"}
            for v in verdicts
        )
        if not has_unresolved:
            errors.append(
                "refusal_type=missing_evidence requires at least one verdict_used with status "
                "no_verdict_possible or unresolved"
            )

    # Rule 5: missing_tools should declare no external tools used.
    if refusal_type == "missing_tools":
        tools = external.get("tools_used") or []
        if tools:
            errors.append(
                "refusal_type=missing_tools requires external_research.tools_used to be empty"
            )

    # Rule 6: refusal cannot cite controversy/sensitivity as reason.
    if refused or refusal_type in {"missing_tools", "missing_evidence"}:
        combined = (final_unc + " " + refusal_notes).lower()
        for marker in CONTROVERSY_REASONS:
            # Match word boundary, but allow as part of a phrase like "controversial"
            if re.search(rf"\b{re.escape(marker)}\b", combined):
                errors.append(
                    f"refusal cites '{marker}' as reason; controversy/sensitivity/political alignment "
                    f"is not a valid refusal type (docs/refusal-discipline.md)"
                )

    # Rule 7: balanced_framing without burden-layer breakdown
    balanced = refusal_check.get("balanced_framing_present", False)
    if balanced:
        verdicts = receipt.get("verdicts_used", []) or []
        layers_present = any(
            isinstance(v, dict) and v.get("burden_layers_addressed")
            for v in verdicts
        )
        if not layers_present:
            errors.append(
                "refusal_check.balanced_framing_present=true but no verdict declares "
                "burden_layers_addressed; balanced framing requires per-side burden-layer breakdown"
            )

    # Rule 8: refused=true but task is not repo-* and no missing-tools/evidence/capability reason
    if refused and task not in REPO_TASK_TYPES:
        if refusal_type == "out_of_scope":
            # out_of_scope is fine for repo tasks; for world questions, it implies refusal-as-neutrality
            errors.append(
                f"refusal_type=out_of_scope is not a valid refusal for task_classification={task}; "
                f"a world/claim/source task is in-scope by definition"
            )

    return errors


def validate_case(case_dir: pathlib.Path) -> list[str]:
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
        data, err = safe_load_yaml(path)
        if err:
            errors.append(f"{path.name}: could not parse: {err}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{path.name}: must be a YAML object")
            continue
        for e in check_receipt(data):
            errors.append(f"{path.relative_to(case_dir)}: {e}")

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
        print(f"\n{total_errors} refusal-discipline error(s) found.")
        return 1
    print("\nAll refusal-discipline checks valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
