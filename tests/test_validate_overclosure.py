"""Tests for scripts/validate_overclosure.py."""

import pathlib

import validate_overclosure

FIXTURE_ROOT = pathlib.Path(__file__).parent / "fixtures" / "overclosure"


def fixture_errors(kind: str, name: str) -> list[str]:
    return validate_overclosure.validate_case(FIXTURE_ROOT / kind / name)


def test_invalid_co_causation_stronger_alternative_only_fails():
    errors = fixture_errors("invalid", "co_causation_stronger_alternative_only")
    assert any("stronger alternative" in error or "stronger primary" in error for error in errors), errors
    assert any("required_chain link" in error for error in errors), errors


def test_invalid_co_causation_missing_positive_evidence_only_fails():
    errors = fixture_errors("invalid", "co_causation_missing_positive_evidence_only")
    assert any("stronger-alternative, missing-link, non-test, non-corroboration, method-gap, or absence" in error for error in errors), errors


def test_invalid_co_causation_official_non_corroboration_only_fails():
    errors = fixture_errors("invalid", "co_causation_official_non_corroboration_only")
    assert any("non-corroboration" in error or "missing-link/alternative" in error for error in errors), errors


def test_invalid_stand3_style_overclosure_fails():
    errors = fixture_errors("invalid", "stand3_style_overclosure")
    assert any("contradicts_directly" in error for error in errors), errors
    assert any("world-causal" in error for error in errors), errors
    assert any("required_chain link" in error for error in errors), errors


def test_invalid_negated_exclusion_with_absence_language_fails():
    errors = fixture_errors("invalid", "negated_exclusion_with_absence_language")
    assert any("contradicts_directly" in error for error in errors), errors
    assert any("world-causal" in error for error in errors), errors
    assert any("required_chain link" in error for error in errors), errors


def test_invalid_causal_chain_contradicted_without_required_chain_fails():
    errors = fixture_errors("invalid", "causal_chain_contradicted_without_required_chain")
    assert any("requires non-empty required_chain" in error for error in errors), errors


def test_invalid_direct_contradiction_no_evidence_found_fails():
    errors = fixture_errors("invalid", "direct_contradiction_no_evidence_found")
    assert any("contradicts_directly" in error and "absence" in error for error in errors), errors


def test_invalid_contradicted_with_unresolved_high_materiality_anomaly_fails():
    errors = fixture_errors("invalid", "contradicted_with_unresolved_high_materiality_anomaly")
    assert any("residual-path-closure" in error for error in errors), errors


def test_valid_causal_temporal_exclusion_contradiction_passes():
    assert fixture_errors("valid", "causal_temporal_exclusion_contradiction") == []


def test_valid_co_causation_downgraded_to_weak_passes():
    assert fixture_errors("valid", "co_causation_downgraded_to_weak") == []


def test_valid_reported_source_report_established_passes():
    assert fixture_errors("valid", "reported_source_report_established") == []


def test_cli_reports_invalid_fixture(capsys):
    exit_code = validate_overclosure.main(str(FIXTURE_ROOT / "invalid" / "co_causation_stronger_alternative_only"))
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL" in captured.out
