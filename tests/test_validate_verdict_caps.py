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
