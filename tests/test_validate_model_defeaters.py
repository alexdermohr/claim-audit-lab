"""Tests for scripts/validate_model_defeaters.py"""

import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_model_defeaters

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "model-defeaters.v1.schema.json"


def write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def write_refs(case_dir):
    write_yaml(case_dir / "sources.yml", {"schema_version": "1.0", "sources": [{"source_id": "s001"}]})
    write_yaml(case_dir / "claims.yml", {"schema_version": "1.0", "claims": [{"claim_id": "c001"}]})
    write_yaml(case_dir / "hypotheses.yml", {"schema_version": "1.0", "hypotheses": [{"id": "h1"}]})
    write_yaml(case_dir / "evidence-pack.yml", {"schema_version": "1.0", "evidence": [{"evidence_id": "e001"}]})


def defeater(**overrides):
    item = {
        "defeater_id": "d001",
        "target_claim_ref": "c001",
        "target_hypothesis_ref": "h1",
        "defeater_type": "model_incompatibility",
        "source_refs": ["s001"],
        "evidence_refs": ["e001"],
        "statement": "Mechanism A is incompatible with observation B.",
        "materiality": 0.8,
        "status": "unresolved",
        "rebuttal_evidence_refs": [],
        "verdict_effect": {"effect": "prevents_strong_closure", "rationale": "Central step is challenged."},
    }
    item.update(overrides)
    return item


def doc(defeaters):
    return {"schema_version": "1.0", "case_ref": "cases/test", "defeaters": defeaters}


def validate(case_dir):
    return validate_model_defeaters.validate_case(case_dir, load_schema())


def test_valid_minimal_defeater_passes(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "model-defeaters.yml", doc([defeater()]))
    assert validate(tmp_path) == []


def test_duplicate_defeater_id_fails(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "model-defeaters.yml", doc([defeater(), defeater(statement="Second")]))
    errors = validate(tmp_path)
    assert any("duplicate defeater_id 'd001'" in e for e in errors), errors


def test_unknown_target_claim_fails(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "model-defeaters.yml", doc([defeater(target_claim_ref="c999")]))
    errors = validate(tmp_path)
    assert any("target_claim_ref 'c999' not found" in e for e in errors), errors


def test_unknown_source_ref_fails(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "model-defeaters.yml", doc([defeater(source_refs=["s999"])]))
    errors = validate(tmp_path)
    assert any("source_ref 's999' not found" in e for e in errors), errors


def test_unknown_evidence_ref_fails(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "model-defeaters.yml", doc([defeater(evidence_refs=["e999"])]))
    errors = validate(tmp_path)
    assert any("evidence_ref 'e999' not found" in e for e in errors), errors


def test_materiality_out_of_range_fails(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "model-defeaters.yml", doc([defeater(materiality=1.5)]))
    errors = validate(tmp_path)
    assert any("Schema error" in e and "materiality" in e for e in errors), errors


def test_no_target_fails(tmp_path):
    write_refs(tmp_path)
    item = defeater()
    item.pop("target_claim_ref")
    item.pop("target_hypothesis_ref")
    write_yaml(tmp_path / "model-defeaters.yml", doc([item]))
    errors = validate(tmp_path)
    assert any("must target at least one" in e for e in errors), errors


def test_resolved_high_materiality_without_rebuttal_fails(tmp_path):
    write_refs(tmp_path)
    write_yaml(
        tmp_path / "model-defeaters.yml",
        doc([defeater(status="resolved", materiality=0.9, rebuttal_evidence_refs=[])]),
    )
    errors = validate(tmp_path)
    assert any("requires at least one rebuttal_evidence_ref" in e for e in errors), errors


def test_resolved_high_materiality_with_rebuttal_passes(tmp_path):
    write_refs(tmp_path)
    write_yaml(
        tmp_path / "model-defeaters.yml",
        doc([defeater(status="resolved", materiality=0.9, rebuttal_evidence_refs=["e001"])]),
    )
    assert validate(tmp_path) == []
