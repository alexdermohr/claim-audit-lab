"""Tests for scripts/validate_model_audit.py"""

import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_model_audit

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "model-audit.v1.schema.json"


def write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def write_refs(case_dir, with_defeaters=False):
    write_yaml(case_dir / "claims.yml", {"schema_version": "1.0", "claims": [{"claim_id": "c001"}]})
    write_yaml(case_dir / "hypotheses.yml", {"schema_version": "1.0", "hypotheses": [{"id": "h1"}]})
    if with_defeaters:
        write_yaml(case_dir / "model-defeaters.yml", {
            "schema_version": "1.0",
            "case_ref": "cases/test",
            "defeaters": [{
                "defeater_id": "d001",
                "target_claim_ref": "c001",
                "defeater_type": "model_incompatibility",
                "statement": "Abstract statement.",
                "materiality": 0.4,
                "status": "unresolved",
            }],
        })


def model(**overrides):
    item = {
        "model_id": "m001",
        "claim_ref": "c001",
        "hypothesis_ref": "h1",
        "model_summary": "Abstract model.",
        "central_chain_steps": ["s_init", "s_propagation"],
        "assumptions_public": 0.5,
        "sensitivity_analysis": 0.5,
        "independent_reproducibility": 0.5,
        "observed_feature_fit": 0.5,
        "adversarial_response_quality": 0.5,
        "unresolved_defeater_refs": [],
        "model_confidence": 0.5,
    }
    item.update(overrides)
    return item


def doc(models):
    return {"schema_version": "1.0", "case_ref": "cases/test", "models": models}


def validate(case_dir):
    return validate_model_audit.validate_case(case_dir, load_schema())


def test_valid_model_audit_passes(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "model-audit.yml", doc([model()]))
    assert validate(tmp_path) == []


def test_unknown_claim_ref_fails(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "model-audit.yml", doc([model(claim_ref="c999")]))
    errors = validate(tmp_path)
    assert any("'c999' not found" in e for e in errors), errors


def test_unknown_hypothesis_ref_fails(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "model-audit.yml", doc([model(hypothesis_ref="h99")]))
    errors = validate(tmp_path)
    assert any("'h99' not found" in e for e in errors), errors


def test_unknown_defeater_ref_fails(tmp_path):
    write_refs(tmp_path, with_defeaters=True)
    write_yaml(tmp_path / "model-audit.yml", doc([model(unresolved_defeater_refs=["d999"])]))
    errors = validate(tmp_path)
    assert any("'d999' not found" in e for e in errors), errors


def test_score_out_of_range_fails(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "model-audit.yml", doc([model(model_confidence=1.5)]))
    errors = validate(tmp_path)
    assert any("Schema error" in e for e in errors), errors


def test_duplicate_model_id_fails(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "model-audit.yml", doc([model(), model(model_summary="Other")]))
    errors = validate(tmp_path)
    assert any("duplicate model_id 'm001'" in e for e in errors), errors
