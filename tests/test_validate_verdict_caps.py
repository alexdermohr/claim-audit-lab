"""Tests for scripts/validate_verdict_caps.py"""

import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_verdict_caps


def write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def claims_doc(status):
    return {
        "schema_version": "1.0",
        "claims": [{
            "schema_version": "1.0",
            "claim_id": "c001",
            "claim_type": "causal_claim",
            "statement": "Mechanism A caused outcome B.",
            "status": status,
            "uncertainty": {"score": 0.5, "causes": []},
            "interpolation": {"score": 0.0, "assumptions": []},
        }],
    }


def defeaters_doc(*, materiality=0.9, status="unresolved", rebuttal_refs=None):
    return {
        "schema_version": "1.0",
        "case_ref": "cases/test",
        "defeaters": [{
            "defeater_id": "d001",
            "target_claim_ref": "c001",
            "defeater_type": "model_incompatibility",
            "statement": "Central step is challenged.",
            "materiality": materiality,
            "status": status,
            "rebuttal_evidence_refs": rebuttal_refs or [],
        }],
    }


def test_strong_verdict_with_unresolved_high_defeater_caps(tmp_path):
    write_yaml(tmp_path / "claims.yml", claims_doc("strongly_supported"))
    write_yaml(tmp_path / "model-defeaters.yml", defeaters_doc())
    errors = validate_verdict_caps.validate_case(tmp_path)
    assert any("is capped by unresolved high-materiality defeater" in e for e in errors), errors


def test_strong_verdict_with_rebuttal_passes(tmp_path):
    write_yaml(tmp_path / "claims.yml", claims_doc("strongly_supported"))
    write_yaml(tmp_path / "model-defeaters.yml", defeaters_doc(rebuttal_refs=["e001"]))
    assert validate_verdict_caps.validate_case(tmp_path) == []


def test_plausible_verdict_with_high_defeater_passes(tmp_path):
    write_yaml(tmp_path / "claims.yml", claims_doc("plausible"))
    write_yaml(tmp_path / "model-defeaters.yml", defeaters_doc())
    assert validate_verdict_caps.validate_case(tmp_path) == []


def test_low_materiality_defeater_does_not_cap(tmp_path):
    write_yaml(tmp_path / "claims.yml", claims_doc("strongly_supported"))
    write_yaml(tmp_path / "model-defeaters.yml", defeaters_doc(materiality=0.3))
    assert validate_verdict_caps.validate_case(tmp_path) == []


def test_resolved_defeater_does_not_cap(tmp_path):
    write_yaml(tmp_path / "claims.yml", claims_doc("strongly_supported"))
    write_yaml(tmp_path / "model-defeaters.yml", defeaters_doc(status="resolved", rebuttal_refs=["e001"]))
    assert validate_verdict_caps.validate_case(tmp_path) == []


def test_established_verdict_is_capped(tmp_path):
    write_yaml(tmp_path / "claims.yml", claims_doc("established"))
    write_yaml(tmp_path / "model-defeaters.yml", defeaters_doc())
    errors = validate_verdict_caps.validate_case(tmp_path)
    assert any("is capped" in e for e in errors), errors


# --- contradicted caps ---

def test_contradicted_verdict_with_unresolved_high_defeater_is_capped(tmp_path):
    write_yaml(tmp_path / "claims.yml", claims_doc("contradicted"))
    write_yaml(tmp_path / "model-defeaters.yml", defeaters_doc())
    errors = validate_verdict_caps.validate_case(tmp_path)
    assert any("is capped" in e and "contradicted" in e for e in errors), errors


def test_contradicted_with_rebuttal_passes(tmp_path):
    write_yaml(tmp_path / "claims.yml", claims_doc("contradicted"))
    write_yaml(tmp_path / "model-defeaters.yml", defeaters_doc(rebuttal_refs=["e001"]))
    assert validate_verdict_caps.validate_case(tmp_path) == []


def test_contradicted_with_low_materiality_defeater_passes(tmp_path):
    write_yaml(tmp_path / "claims.yml", claims_doc("contradicted"))
    write_yaml(tmp_path / "model-defeaters.yml", defeaters_doc(materiality=0.4))
    assert validate_verdict_caps.validate_case(tmp_path) == []


# --- source_report exemption ---

def source_report_claims_doc(status):
    return {
        "schema_version": "1.0",
        "claims": [{
            "schema_version": "1.0",
            "claim_id": "c001",
            "claim_type": "factual_event_claim",
            "claim_kind": "reported_claim",
            "burden_profile": "source_report",
            "statement": "Source X reports that event Y occurred.",
            "status": status,
            "uncertainty": {"score": 0.1, "causes": []},
            "interpolation": {"score": 0.0, "assumptions": []},
        }],
    }


def test_source_report_established_is_exempt_from_cap(tmp_path):
    write_yaml(tmp_path / "claims.yml", source_report_claims_doc("established"))
    write_yaml(tmp_path / "model-defeaters.yml", defeaters_doc())
    assert validate_verdict_caps.validate_case(tmp_path) == []


def test_source_report_strongly_supported_is_exempt_from_cap(tmp_path):
    write_yaml(tmp_path / "claims.yml", source_report_claims_doc("strongly_supported"))
    write_yaml(tmp_path / "model-defeaters.yml", defeaters_doc())
    assert validate_verdict_caps.validate_case(tmp_path) == []


def test_source_report_contradicted_is_not_exempt(tmp_path):
    # Negative closure is not exempt even for source_report claims.
    write_yaml(tmp_path / "claims.yml", source_report_claims_doc("contradicted"))
    write_yaml(tmp_path / "model-defeaters.yml", defeaters_doc())
    errors = validate_verdict_caps.validate_case(tmp_path)
    assert any("is capped" in e for e in errors), errors


def test_source_report_exemption_works_without_claim_kind(tmp_path):
    # claim_kind is optional in the schema; burden_profile alone must be
    # sufficient to identify a source_report claim and apply the exemption.
    doc = source_report_claims_doc("established")
    doc["claims"][0].pop("claim_kind")
    write_yaml(tmp_path / "claims.yml", doc)
    write_yaml(tmp_path / "model-defeaters.yml", defeaters_doc())
    assert validate_verdict_caps.validate_case(tmp_path) == []
