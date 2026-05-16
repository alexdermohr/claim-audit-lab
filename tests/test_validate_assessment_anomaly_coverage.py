"""Tests for scripts/validate_assessment_anomaly_coverage.py"""

import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_assessment_anomaly_coverage


def write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def ledger(materiality=0.8):
    return {
        "schema_version": "1.0",
        "case_ref": "cases/test",
        "anomalies": [
            {
                "anomaly_id": "a001",
                "anomaly_type": "method_gap",
                "statement": "A material method gap exists.",
                "materiality": materiality,
                "anomaly_direction": "increases_uncertainty",
                "status": "unresolved",
            }
        ],
    }



def integrity(materiality=0.8):
    return {
        "schema_version": "1.0",
        "case_ref": "cases/test",
        "investigations": [
            {
                "investigation_id": "inv001",
                "source_cluster_refs": ["s001"],
                "lead_institution": "Test institution",
                "report_role": "primary_investigation",
                "politically_sensitive": True,
                "financially_sensitive": False,
                "institutional_interest_risk": 0.7,
                "hypothesis_space_declared": ["Main hypothesis"],
                "hypothesis_space_gaps": ["Untested alternative"],
                "non_tested_material_paths": [
                    {
                        "path_id": "nt001",
                        "expected_test": "Independent replication",
                        "justification_present": "partial",
                        "justification_quality": 0.4,
                        "materiality": materiality,
                    }
                ],
                "adversarial_review": {"present": "partial", "notes": "Limited challenge."},
                "integrity_verdict": "methodologically_strong_but_incompletely_adversarial",
                "downstream_constraints": ["Do not overclose."],
            }
        ],
    }


def test_high_materiality_anomaly_referenced_in_assessment_passes(tmp_path):
    write_yaml(tmp_path / "anomaly-ledger.yml", ledger(0.8))
    (tmp_path / "assessment.md").write_text("The caveat is tracked as anomaly a001.", encoding="utf-8")
    assert validate_assessment_anomaly_coverage.validate_case(tmp_path) == []


def test_high_materiality_anomaly_missing_from_assessment_fails(tmp_path):
    write_yaml(tmp_path / "anomaly-ledger.yml", ledger(0.8))
    (tmp_path / "assessment.md").write_text("No anomaly reference here.", encoding="utf-8")
    errors = validate_assessment_anomaly_coverage.validate_case(tmp_path)
    assert any("high-materiality anomaly a001" in e for e in errors), errors


def test_low_materiality_anomaly_does_not_require_assessment_reference(tmp_path):
    write_yaml(tmp_path / "anomaly-ledger.yml", ledger(0.4))
    (tmp_path / "assessment.md").write_text("No anomaly reference here.", encoding="utf-8")
    assert validate_assessment_anomaly_coverage.validate_case(tmp_path) == []


def test_missing_assessment_does_not_duplicate_topology_failure(tmp_path):
    write_yaml(tmp_path / "anomaly-ledger.yml", ledger(0.8))
    assert validate_assessment_anomaly_coverage.validate_case(tmp_path) == []


def test_high_materiality_non_tested_path_referenced_in_assessment_passes(tmp_path):
    write_yaml(tmp_path / "investigation-integrity.yml", integrity(0.8))
    (tmp_path / "assessment.md").write_text("The non-test nt001 limits closure.", encoding="utf-8")
    assert validate_assessment_anomaly_coverage.validate_case(tmp_path) == []


def test_high_materiality_non_tested_path_missing_from_assessment_fails(tmp_path):
    write_yaml(tmp_path / "investigation-integrity.yml", integrity(0.8))
    (tmp_path / "assessment.md").write_text("No non-test reference here.", encoding="utf-8")
    errors = validate_assessment_anomaly_coverage.validate_case(tmp_path)
    assert any("high-materiality non-tested path nt001" in e for e in errors), errors


def test_low_materiality_non_tested_path_does_not_require_assessment_reference(tmp_path):
    write_yaml(tmp_path / "investigation-integrity.yml", integrity(0.4))
    (tmp_path / "assessment.md").write_text("No non-test reference here.", encoding="utf-8")
    assert validate_assessment_anomaly_coverage.validate_case(tmp_path) == []


def test_missing_assessment_for_non_tested_path_does_not_duplicate_topology_failure(tmp_path):
    write_yaml(tmp_path / "investigation-integrity.yml", integrity(0.8))
    assert validate_assessment_anomaly_coverage.validate_case(tmp_path) == []
