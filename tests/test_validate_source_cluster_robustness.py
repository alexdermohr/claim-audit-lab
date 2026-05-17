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


# Fix 7 / Fix 8: New fixtures


def test_invalid_partial_cluster_coverage_not_enough_fails():
    """Fix 3: partial cluster coverage must be rejected; all flagged sources must be covered."""
    errors = fixture_errors("invalid", "partial_cluster_coverage_not_enough")
    assert any("partial coverage is not enough" in e for e in errors), errors


def test_invalid_high_verdict_without_remaining_support_fails():
    """Fix 5: if no supporting relation remains after knockout, a plausible/higher verdict is rejected."""
    errors = fixture_errors("invalid", "high_verdict_without_remaining_support")
    assert any("not supported by remaining evidence relations" in e for e in errors), errors


def test_valid_german_fragility_visible_passes():
    """Fix 2: German fragility terms (Quellencluster-Abhängigkeit etc.) satisfy assessment visibility."""
    errors = fixture_errors("valid", "german_fragility_visible")
    assert errors == [], errors


def test_invalid_duplicate_cluster_id_fails():
    """Fix 4: duplicate cluster_id must produce an error."""
    errors = fixture_errors("invalid", "duplicate_cluster_id")
    assert any("Duplicate cluster_id" in e for e in errors), errors


def test_invalid_duplicate_test_id_fails():
    """Fix 4: duplicate test_id must produce an error."""
    errors = fixture_errors("invalid", "duplicate_test_id")
    assert any("Duplicate test_id" in e for e in errors), errors
