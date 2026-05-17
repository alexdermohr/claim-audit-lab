"""Tests for scripts/validate_source_cluster_robustness.py."""

import pathlib

import validate_source_cluster_robustness

FIXTURE_ROOT = pathlib.Path(__file__).parent / "fixtures" / "source_cluster_robustness"
SCHEMA = validate_source_cluster_robustness.load_schema()


def fixture_errors(kind: str, name: str) -> list[str]:
    return validate_source_cluster_robustness.validate_case(FIXTURE_ROOT / kind / name, SCHEMA)


def test_valid_source_cluster_robustness_declared_passes():
    errors = fixture_errors("valid", "source_cluster_robustness_declared")
    assert errors == [], errors


def test_invalid_missing_robustness_for_strong_causal_claim_fails():
    errors = fixture_errors("invalid", "missing_robustness_for_strong_causal_claim")
    assert any("source-cluster-robustness.yml required" in e for e in errors), errors


def test_invalid_unknown_source_ref_in_cluster_fails():
    errors = fixture_errors("invalid", "unknown_source_ref_in_cluster")
    assert any("s999" in e and "not found in sources.yml" in e for e in errors), errors


def test_invalid_unknown_claim_ref_in_knockout_fails():
    errors = fixture_errors("invalid", "unknown_claim_ref_in_knockout")
    assert any("c999" in e and "not found in claims.yml" in e for e in errors), errors


def test_invalid_high_fragility_not_assessment_visible_fails():
    errors = fixture_errors("invalid", "high_fragility_not_assessment_visible")
    assert any("assessment.md must surface" in e for e in errors), errors


def test_invalid_compromise_treatment_fails():
    errors = fixture_errors("invalid", "invalid_compromise_treatment")
    # Schema enum rejects the unknown value; validator also reports the unknown treatment.
    assert any("treatment" in e for e in errors), errors


def test_invalid_compromise_upgraded_to_proof_fails():
    errors = fixture_errors("invalid", "compromise_upgraded_to_proof")
    assert any("positive proof" in e for e in errors), errors


def test_main_accepts_valid_fixture_path(tmp_path, monkeypatch):
    target = FIXTURE_ROOT / "valid" / "source_cluster_robustness_declared"
    assert validate_source_cluster_robustness.main(str(target)) == 0
