"""Tests for scripts/validate_anomaly_ledger.py"""

import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_anomaly_ledger

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "anomaly-ledger.v1.schema.json"


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


def anomaly(**overrides):
    item = {
        "anomaly_id": "a001",
        "anomaly_type": "method_gap",
        "source_refs": ["s001"],
        "affected_claims": ["c001"],
        "affected_hypotheses": ["h1"],
        "statement": "An expected method check is not documented.",
        "materiality": 0.8,
        "anomaly_direction": "increases_uncertainty",
        "why_it_matters": "The claim leans on the untested method path.",
        "possible_benign_explanations": ["The check may have been performed but summarized elsewhere."],
        "possible_bias_explanations": ["The untested path could align with institutional incentives."],
        "missing_for_resolution": ["Raw method appendix or replication package."],
        "status": "unresolved",
        "verdict_effect": {"claim_ref": "c001", "effect": "prevents_overconfidence"},
    }
    item.update(overrides)
    return item


def ledger(anomalies):
    return {"schema_version": "1.0", "case_ref": "cases/test", "anomalies": anomalies}


def validate(case_dir):
    return validate_anomaly_ledger.validate_case(case_dir, load_schema())


def test_valid_minimal_anomaly_ledger_passes(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "anomaly-ledger.yml", ledger([anomaly()]))
    assert validate(tmp_path) == []


def test_duplicate_anomaly_ids_fail(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "anomaly-ledger.yml", ledger([anomaly(), anomaly(statement="Second")]))
    errors = validate(tmp_path)
    assert any("duplicate anomaly_id 'a001'" in e for e in errors), errors


def test_unknown_source_ref_fails(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "anomaly-ledger.yml", ledger([anomaly(source_refs=["s999"])]))
    errors = validate(tmp_path)
    assert any("source_ref 's999' not found" in e for e in errors), errors


def test_unknown_affected_claim_fails(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "anomaly-ledger.yml", ledger([anomaly(affected_claims=["c999"])]))
    errors = validate(tmp_path)
    assert any("affected_claim 'c999' not found" in e for e in errors), errors


def test_high_materiality_without_benign_explanation_fails(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "anomaly-ledger.yml", ledger([anomaly(possible_benign_explanations=[])]))
    errors = validate(tmp_path)
    assert any("possible_benign_explanations" in e for e in errors), errors


def test_high_materiality_without_bias_explanation_fails(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "anomaly-ledger.yml", ledger([anomaly(possible_bias_explanations=[])]))
    errors = validate(tmp_path)
    assert any("possible_bias_explanations" in e for e in errors), errors


def test_high_materiality_without_missing_for_resolution_fails(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "anomaly-ledger.yml", ledger([anomaly(missing_for_resolution=[])]))
    errors = validate(tmp_path)
    assert any("missing_for_resolution" in e for e in errors), errors


def test_anomaly_schema_does_not_require_declaring_manipulation_as_fact(tmp_path):
    write_refs(tmp_path)
    item = anomaly(possible_bias_explanations=["A bias explanation remains only a hypothesis."])
    assert "manipulation" not in item
    write_yaml(tmp_path / "anomaly-ledger.yml", ledger([item]))
    assert validate(tmp_path) == []


def test_malformed_claims_top_level_arrays_fail(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "anomaly-ledger.yml", ledger([anomaly()]))
    for malformed in (None, "c001", {"claim_id": "c001"}):
        write_yaml(tmp_path / "claims.yml", {"schema_version": "1.0", "claims": malformed})
        errors = validate(tmp_path)
        assert any("claims.yml 'claims' must be an array" in e for e in errors), errors


def test_malformed_sources_top_level_arrays_fail(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "anomaly-ledger.yml", ledger([anomaly()]))
    for malformed in (None, "s001", {"source_id": "s001"}):
        write_yaml(tmp_path / "sources.yml", {"schema_version": "1.0", "sources": malformed})
        errors = validate(tmp_path)
        assert any("sources.yml 'sources' must be an array" in e for e in errors), errors


def test_malformed_hypotheses_top_level_arrays_fail(tmp_path):
    write_refs(tmp_path)
    write_yaml(tmp_path / "anomaly-ledger.yml", ledger([anomaly()]))
    for malformed in (None, "h1", {"id": "h1"}):
        write_yaml(tmp_path / "hypotheses.yml", {"schema_version": "1.0", "hypotheses": malformed})
        errors = validate(tmp_path)
        assert any("hypotheses.yml 'hypotheses' must be an array" in e for e in errors), errors


def test_anomaly_reference_lists_with_non_string_items_fail_without_traceback(tmp_path):
    write_refs(tmp_path)
    item = anomaly(
        source_refs=["s001", {"bad": "source"}, ["s002"], 7],
        affected_claims=["c001", {"bad": "claim"}, ["c002"], 8],
        affected_hypotheses=["h1", {"bad": "hypothesis"}, ["h2"], 9],
    )
    write_yaml(tmp_path / "anomaly-ledger.yml", ledger([item]))

    errors = validate(tmp_path)

    assert any("anomaly 'a001' source_refs[1] must be a string" in e for e in errors), errors
    assert any("anomaly 'a001' source_refs[2] must be a string" in e for e in errors), errors
    assert any("anomaly 'a001' source_refs[3] must be a string" in e for e in errors), errors
    assert any("anomaly 'a001' affected_claims[1] must be a string" in e for e in errors), errors
    assert any("anomaly 'a001' affected_hypotheses[1] must be a string" in e for e in errors), errors
    assert not any("Traceback" in e for e in errors)
