"""Tests for scripts/validate_burden_layers.py"""

import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_burden_layers

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "burden-layers.v1.schema.json"


def write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def write_refs(case_dir):
    write_yaml(case_dir / "claims.yml", {"schema_version": "1.0", "claims": [{"claim_id": "c001"}]})
    write_yaml(case_dir / "evidence-pack.yml", {"schema_version": "1.0", "evidence": [{"evidence_id": "e001"}]})


def doc(entries):
    return {"schema_version": "1.0", "case_ref": "cases/test", "claims": entries}


def validate(case_dir):
    return validate_burden_layers.validate_case(case_dir, load_schema())


def test_valid_burden_layers_passes(tmp_path):
    write_refs(tmp_path)
    write_yaml(
        tmp_path / "burden-layers.yml",
        doc([
            {
                "claim_ref": "c001",
                "burden_profile": "causal_chain",
                "layers": {
                    "physical_mechanism": {"status": "unresolved", "evidence_refs": ["e001"]},
                    "operational_placement": {"status": "missing", "evidence_refs": []},
                    "actor_attribution": {"status": "out_of_scope", "evidence_refs": []},
                },
            }
        ]),
    )
    assert validate(tmp_path) == []


def test_unknown_claim_ref_fails(tmp_path):
    write_refs(tmp_path)
    write_yaml(
        tmp_path / "burden-layers.yml",
        doc([{"claim_ref": "c999", "layers": {"physical_mechanism": {"status": "unresolved"}}}]),
    )
    errors = validate(tmp_path)
    assert any("'c999' not found" in e for e in errors), errors


def test_unknown_evidence_ref_fails(tmp_path):
    write_refs(tmp_path)
    write_yaml(
        tmp_path / "burden-layers.yml",
        doc([{
            "claim_ref": "c001",
            "layers": {"physical_mechanism": {"status": "unresolved", "evidence_refs": ["e999"]}},
        }]),
    )
    errors = validate(tmp_path)
    assert any("'e999' not found" in e for e in errors), errors


def test_invalid_layer_status_fails(tmp_path):
    write_refs(tmp_path)
    write_yaml(
        tmp_path / "burden-layers.yml",
        doc([{"claim_ref": "c001", "layers": {"physical_mechanism": {"status": "bogus_status"}}}]),
    )
    errors = validate(tmp_path)
    assert any("Schema error" in e for e in errors), errors


def test_duplicate_claim_ref_fails(tmp_path):
    write_refs(tmp_path)
    write_yaml(
        tmp_path / "burden-layers.yml",
        doc([
            {"claim_ref": "c001", "layers": {"physical_mechanism": {"status": "unresolved"}}},
            {"claim_ref": "c001", "layers": {"physical_mechanism": {"status": "resolved"}}},
        ]),
    )
    errors = validate(tmp_path)
    assert any("duplicate burden-layer claim_ref 'c001'" in e for e in errors), errors


# --- anti-knockout rule ---

def write_claim_with_status(case_dir, status):
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "claims.yml").write_text(
        __import__("yaml").safe_dump({
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
        }),
        encoding="utf-8",
    )
    (case_dir / "evidence-pack.yml").write_text(
        __import__("yaml").safe_dump({"schema_version": "1.0", "evidence": []}),
        encoding="utf-8",
    )


def anti_knockout_layers(physical_status="contested", op_status="missing"):
    return {
        "physical_mechanism": {"status": physical_status},
        "operational_placement": {"status": op_status},
    }


def test_anti_knockout_contradicted_with_open_mechanism_fails(tmp_path):
    write_claim_with_status(tmp_path, "contradicted")
    write_yaml(
        tmp_path / "burden-layers.yml",
        doc([{"claim_ref": "c001", "layers": anti_knockout_layers()}]),
    )
    errors = validate(tmp_path)
    assert any("anti-knockout" in e for e in errors), errors


def test_anti_knockout_weak_with_open_mechanism_fails(tmp_path):
    write_claim_with_status(tmp_path, "weak")
    write_yaml(
        tmp_path / "burden-layers.yml",
        doc([{"claim_ref": "c001", "layers": anti_knockout_layers()}]),
    )
    errors = validate(tmp_path)
    assert any("anti-knockout" in e for e in errors), errors


def test_anti_knockout_contradicted_with_resolved_mechanism_passes(tmp_path):
    write_claim_with_status(tmp_path, "contradicted")
    write_yaml(
        tmp_path / "burden-layers.yml",
        doc([{"claim_ref": "c001", "layers": anti_knockout_layers(physical_status="resolved")}]),
    )
    errors = validate(tmp_path)
    assert not any("anti-knockout" in e for e in errors), errors


def test_anti_knockout_plausible_verdict_passes(tmp_path):
    write_claim_with_status(tmp_path, "plausible")
    write_yaml(
        tmp_path / "burden-layers.yml",
        doc([{"claim_ref": "c001", "layers": anti_knockout_layers()}]),
    )
    assert validate(tmp_path) == []


def test_anti_knockout_operational_placement_not_missing_passes(tmp_path):
    write_claim_with_status(tmp_path, "contradicted")
    write_yaml(
        tmp_path / "burden-layers.yml",
        doc([{
            "claim_ref": "c001",
            "layers": {"physical_mechanism": {"status": "contested"}, "operational_placement": {"status": "resolved"}},
        }]),
    )
    errors = validate(tmp_path)
    assert not any("anti-knockout" in e for e in errors), errors


def test_anti_knockout_structural_effect_unresolved_also_triggers(tmp_path):
    write_claim_with_status(tmp_path, "weak")
    write_yaml(
        tmp_path / "burden-layers.yml",
        doc([{
            "claim_ref": "c001",
            "layers": {
                "structural_effect": {"status": "unresolved"},
                "operational_placement": {"status": "missing"},
            },
        }]),
    )
    errors = validate(tmp_path)
    assert any("anti-knockout" in e for e in errors), errors
