#!/usr/bin/env python3
"""Validate red-team review independence and high-finding resolution.

Rules:
1. If reviewer_independence.status is self_review or unknown,
   verdict.status must not be passed or passed_with_notes.
   Allowed: pending, blocked, self_review_only, pending_independent_review.

2. If reviewer_independence is absent, apply heuristic on reviewer field:
   names matching known non-independent patterns (assistant, claude, agent,
   self, bot, generated, case-author, same_agent, pending, or empty)
   must not have verdict passed/passed_with_notes.

3. If any finding has severity=high and either lacks status or has
   status != resolved (or resolution_refs is empty), verdict must not be
   passed or passed_with_notes.
"""

from __future__ import annotations

import pathlib
import re
import sys

import yaml

PASS_STATUSES = {"passed", "passed_with_notes"}

NON_INDEPENDENT_PATTERNS = re.compile(
    r"(?:^$"
    r"|pending"
    r"|case.?author"
    r"|assistant"
    r"|claude"
    r"|\bagent\b"
    r"|same.?agent"
    r"|\bself\b"
    r"|generated"
    r"|\bbot\b"
    r")",
    re.IGNORECASE,
)

CASE_MARKERS = (
    "claims.yml",
    "evidence-relations.yml",
    "anomaly-ledger.yml",
    "investigation-integrity.yml",
)


def is_case_dir(path: pathlib.Path) -> bool:
    return any((path / marker).exists() for marker in CASE_MARKERS)


def discover_case_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    candidate_dirs = {root}
    for marker in CASE_MARKERS:
        candidate_dirs.update(path.parent for path in root.rglob(marker))
    return sorted(
        d
        for d in candidate_dirs
        if d.is_dir() and "_template" not in d.parts and is_case_dir(d)
    )


def _is_non_independent_reviewer(reviewer: str) -> bool:
    return bool(NON_INDEPENDENT_PATTERNS.search(reviewer.strip()))


def _finding_is_unresolved_high(finding: dict) -> bool:
    if finding.get("severity") != "high":
        return False
    status = finding.get("status")
    if status != "resolved":
        return True
    resolution_refs = finding.get("resolution_refs")
    if not resolution_refs:
        return True
    return False


def validate_case(case_dir: pathlib.Path) -> list[str]:
    rt_file = case_dir / "redteam.yml"
    if not rt_file.exists():
        return []

    try:
        with open(rt_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        return [f"FAIL {rt_file}: Could not parse YAML: {e}"]

    if not isinstance(data, dict):
        return []

    verdict = data.get("verdict") or {}
    verdict_status = verdict.get("status", "")
    reviewer = data.get("reviewer")
    reviewer_independence = data.get("reviewer_independence")
    findings = data.get("findings") or []

    errors: list[str] = []

    # --- Rule 1 & 2: Reviewer Independence ---
    if isinstance(reviewer_independence, dict):
        indep_status = reviewer_independence.get("status", "unknown")
        if indep_status in ("self_review", "unknown"):
            if verdict_status in PASS_STATUSES:
                errors.append(
                    f"FAIL {rt_file}: verdict.status: "
                    f"reviewer_independence.status is '{indep_status}' but "
                    f"verdict.status is '{verdict_status}'. "
                    f"Self-review or unknown reviewer cannot produce a pass verdict. "
                    f"Use self_review_only or pending_independent_review instead."
                )
    else:
        # Fallback heuristic on reviewer string
        reviewer_str = str(reviewer or "")
        if _is_non_independent_reviewer(reviewer_str):
            if verdict_status in PASS_STATUSES:
                errors.append(
                    f"FAIL {rt_file}: verdict.status: "
                    f"reviewer '{reviewer_str or '<empty>'}' matches non-independent reviewer pattern "
                    f"but verdict.status is '{verdict_status}'. "
                    f"Add reviewer_independence.status: self_review and change "
                    f"verdict.status to self_review_only (if no high findings) "
                    f"or blocked (if high findings present)."
                )

    # --- Rule 3: High Finding Gate ---
    if verdict_status in PASS_STATUSES:
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            if _finding_is_unresolved_high(finding):
                fid = finding.get("id", "<unknown>")
                fstatus = finding.get("status", "<absent>")
                errors.append(
                    f"FAIL {rt_file}: verdict.status: "
                    f"finding {fid} has severity=high and status={fstatus!r} "
                    f"but verdict.status is '{verdict_status}'. "
                    f"High findings require status: resolved and non-empty "
                    f"resolution_refs before a pass verdict is allowed. "
                    f"Set verdict.status: blocked until finding {fid} is resolved."
                )

    return errors


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    case_dirs = discover_case_dirs(root)

    if not case_dirs:
        print(f"No case directories found under {root}")
        return 0

    total_errors: list[str] = []
    for case_dir in case_dirs:
        errs = validate_case(case_dir)
        total_errors.extend(errs)

    if total_errors:
        for err in total_errors:
            print(err)
        print(f"\n{len(total_errors)} error(s) found.")
        return 1

    for case_dir in case_dirs:
        print(f"OK   {case_dir}")
    print("\nAll red-team independence checks valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
