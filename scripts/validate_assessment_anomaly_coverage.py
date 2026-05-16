#!/usr/bin/env python3
"""Validate that high-materiality anomalies and non-tests are visible in assessment.md."""

import pathlib
import re
import sys

import yaml

HIGH_MATERIALITY = 0.7


def safe_load_yaml(path: pathlib.Path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except Exception as exc:
        return None, str(exc)


def assessment_mentions_anomaly(text: str, anomaly_id: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_-])(?:anomaly\s+)?{re.escape(anomaly_id)}(?![A-Za-z0-9_-])", text, re.I) is not None


def assessment_mentions_non_tested_path(text: str, path_id: str) -> bool:
    prefix = r"(?:non[-_]tested_material_path|non[- ]tested\s+path|non[- ]test)\s+"
    return re.search(rf"(?<![A-Za-z0-9_-])(?:{prefix})?{re.escape(path_id)}(?![A-Za-z0-9_-])", text, re.I) is not None


def validate_anomaly_coverage(case_dir: pathlib.Path, assessment: str) -> list[str]:
    ledger_path = case_dir / "anomaly-ledger.yml"
    if not ledger_path.exists():
        return []

    data, err = safe_load_yaml(ledger_path)
    if err:
        return [f"Could not parse anomaly-ledger.yml: {err}"]
    if not isinstance(data, dict):
        return ["anomaly-ledger.yml must contain a YAML object."]

    errors: list[str] = []
    anomalies = data.get("anomalies", [])
    if not isinstance(anomalies, list):
        return []
    for anomaly in anomalies:
        if not isinstance(anomaly, dict):
            continue
        anomaly_id = anomaly.get("anomaly_id", "?")
        materiality = anomaly.get("materiality")
        if isinstance(materiality, (int, float)) and materiality >= HIGH_MATERIALITY:
            if not assessment_mentions_anomaly(assessment, anomaly_id):
                errors.append(
                    f"high-materiality anomaly {anomaly_id} materiality={materiality:.2f} is not referenced in assessment.md"
                )
    return errors


def validate_integrity_non_test_coverage(case_dir: pathlib.Path, assessment: str) -> list[str]:
    integrity_path = case_dir / "investigation-integrity.yml"
    if not integrity_path.exists():
        return []

    data, err = safe_load_yaml(integrity_path)
    if err:
        return [f"Could not parse investigation-integrity.yml: {err}"]
    if not isinstance(data, dict):
        return ["investigation-integrity.yml must contain a YAML object."]

    errors: list[str] = []
    investigations = data.get("investigations", [])
    if not isinstance(investigations, list):
        return []
    for investigation in investigations:
        if not isinstance(investigation, dict):
            continue
        for path in investigation.get("non_tested_material_paths") or []:
            if not isinstance(path, dict):
                continue
            path_id = path.get("path_id", "?")
            materiality = path.get("materiality")
            if isinstance(materiality, (int, float)) and materiality >= HIGH_MATERIALITY:
                if not assessment_mentions_non_tested_path(assessment, path_id):
                    errors.append(
                        f"high-materiality non-tested path {path_id} materiality={materiality:.2f} is not referenced in assessment.md"
                    )
    return errors


def validate_case(case_dir: pathlib.Path) -> list[str]:
    if not (case_dir / "anomaly-ledger.yml").exists() and not (case_dir / "investigation-integrity.yml").exists():
        return []
    assessment_path = case_dir / "assessment.md"
    if not assessment_path.exists():
        return []

    try:
        assessment = assessment_path.read_text(encoding="utf-8")
    except Exception as exc:
        return [f"Could not read assessment.md: {exc}"]

    errors: list[str] = []
    errors.extend(validate_anomaly_coverage(case_dir, assessment))
    errors.extend(validate_integrity_non_test_coverage(case_dir, assessment))
    return errors


def discover_case_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    markers = list(root.rglob("anomaly-ledger.yml")) + list(root.rglob("investigation-integrity.yml"))
    return sorted({marker.parent for marker in markers if "_template" not in marker.parts})


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    case_dirs = discover_case_dirs(root)
    if not case_dirs:
        print(f"No anomaly-ledger.yml or investigation-integrity.yml files found under {root}")
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
        print(f"\n{total_errors} assessment critical-inquiry coverage error(s) found.")
        return 1
    print("\nAll high-materiality anomalies and non-tested paths are assessment-visible.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
