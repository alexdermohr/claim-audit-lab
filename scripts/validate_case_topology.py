#!/usr/bin/env python3
"""Validate required artifact topology for claim-audit case roots."""

import pathlib
import sys
from case_compat import is_legacy_case, legacy_case_error, legacy_case_until

CASE_ARTIFACTS = {
    "question.md",
    "claims.yml",
    "sources.yml",
    "evidence-pack.yml",
    "evidence-relations.yml",
    "hypotheses.yml",
    "hypothesis-support-ledger.yml",
    "assessment.md",
    "lifecycle.yml",
    "redteam.yml",
    "redteam.md",
    "contradictions.yml",
    "anomaly-ledger.yml",
    "investigation-integrity.yml",
}


def is_case_root(path: pathlib.Path) -> bool:
    return any((path / artifact).exists() for artifact in CASE_ARTIFACTS)


def discover_case_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    candidate_dirs = {root}
    for artifact in CASE_ARTIFACTS:
        candidate_dirs.update(marker.parent for marker in root.rglob(artifact))
    return sorted(
        d for d in candidate_dirs
        if d.is_dir() and "_template" not in d.parts and is_case_root(d)
    )


def require(errors: list[str], case_dir: pathlib.Path, required: str, because: str) -> None:
    if not (case_dir / required).exists():
        errors.append(f"{required} required because {because}.")


def validate_case(case_dir: pathlib.Path) -> list[str]:
    legacy_error = legacy_case_error(case_dir)
    if legacy_error:
        return [legacy_error]
    if is_legacy_case(case_dir):
        return []

    errors: list[str] = []
    has_claims = (case_dir / "claims.yml").exists()
    has_evidence = (case_dir / "evidence-pack.yml").exists()
    has_assessment = (case_dir / "assessment.md").exists()
    has_hypotheses = (case_dir / "hypotheses.yml").exists()
    has_redteam = (case_dir / "redteam.yml").exists() or (case_dir / "redteam.md").exists()
    has_anomaly_ledger = (case_dir / "anomaly-ledger.yml").exists()
    has_investigation_integrity = (case_dir / "investigation-integrity.yml").exists()

    if has_claims:
        require(errors, case_dir, "evidence-pack.yml", "claims.yml exists")
        require(errors, case_dir, "evidence-relations.yml", "claims.yml exists")

    if has_evidence:
        require(errors, case_dir, "claims.yml", "evidence-pack.yml exists")
        require(errors, case_dir, "sources.yml", "evidence-pack.yml exists")
        require(errors, case_dir, "evidence-relations.yml", "evidence-pack.yml exists")

    if has_assessment:
        require(errors, case_dir, "claims.yml", "assessment.md exists")
        require(errors, case_dir, "evidence-pack.yml", "assessment.md exists")
        require(errors, case_dir, "evidence-relations.yml", "assessment.md exists")
        require(errors, case_dir, "lifecycle.yml", "assessment.md exists")

    if has_hypotheses:
        require(errors, case_dir, "hypothesis-support-ledger.yml", "hypotheses.yml exists")

    if has_redteam:
        require(errors, case_dir, "assessment.md", "redteam.yml or redteam.md exists")
        require(errors, case_dir, "lifecycle.yml", "redteam.yml or redteam.md exists")

    if has_anomaly_ledger:
        require(errors, case_dir, "claims.yml", "anomaly-ledger.yml exists")
        require(errors, case_dir, "sources.yml", "anomaly-ledger.yml exists")
        require(errors, case_dir, "assessment.md", "anomaly-ledger.yml exists")

    if has_investigation_integrity:
        require(errors, case_dir, "sources.yml", "investigation-integrity.yml exists")
        require(errors, case_dir, "claims.yml", "investigation-integrity.yml exists")
        require(errors, case_dir, "assessment.md", "investigation-integrity.yml exists")

    return errors


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    case_dirs = discover_case_dirs(root)

    if not case_dirs:
        print(f"No case directories found under {root}")
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
            print(f"LEGACY {case_dir}: topology temporarily exempt until {legacy_case_until(case_dir)}")
            continue
        errors = validate_case(case_dir)
        if errors:
            print(f"FAIL {case_dir}:")
            for error in errors:
                print(f"  {error}")
            total_errors += len(errors)
        else:
            print(f"OK   {case_dir}")

    if total_errors:
        print(f"\n{total_errors} case-topology error(s) found.")
        return 1

    print("\nAll case topologies valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
