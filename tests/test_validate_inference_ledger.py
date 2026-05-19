"""Tests for scripts/validate_inference_ledger.py"""

import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_inference_ledger

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "inference-ledger.v1.schema.json"


def write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def write_base(case_dir, claims, evidence=None):
    """Write minimal claims.yml and evidence-pack.yml for a test case."""
    write_yaml(case_dir / "claims.yml", {"schema_version": "1.0", "claims": claims})
    evs = evidence if evidence is not None else [{"evidence_id": "e001"}]
    write_yaml(case_dir / "evidence-pack.yml", {"schema_version": "1.0", "evidence": evs})


def claim(**overrides):
    base = {
        "claim_id": "c001",
        "claim_type": "factual_event_claim",
        "status": "plausible",
    }
    base.update(overrides)
    return base


def ledger(inferences):
    return {"schema_version": "1.0", "case_ref": "cases/test", "inferences": inferences}


def inference(**overrides):
    base = {
        "inference_id": "inf001",
        "claim_ref": "c001",
        "triggered_by": "strong_positive_verdict",
        "inference_steps": [step()],
    }
    base.update(overrides)
    return base


def step(**overrides):
    base = {
        "step_id": "step001",
        "premise_evidence_refs": ["e001"],
        "premise_claim_refs": [],
        "operation": "corroboration",
        "produces": "Corroborated claim from evidence.",
        "uncertainty_effect": "lowers",
        "forbidden_upgrade_checked": ["source_prestige_to_truth"],
    }
    base.update(overrides)
    return base


def validate(case_dir):
    return validate_inference_ledger.validate_case(case_dir, load_schema())


# --- valid cases ---

def test_valid_strongly_supported_with_ledger_and_evidence_ref(tmp_path):
    write_base(tmp_path, [claim(status="strongly_supported")])
    write_yaml(tmp_path / "inference-ledger.yml", ledger([inference()]))
    assert validate(tmp_path) == []


def test_valid_reported_claim_established_no_ledger(tmp_path):
    """reported_claim is exempt: established status does not require inference-ledger."""
    write_base(tmp_path, [claim(status="established", claim_kind="reported_claim")])
    assert validate(tmp_path) == []


def test_valid_source_report_burden_established_no_ledger(tmp_path):
    """burden_profile=source_report is exempt from inference-ledger requirement."""
    write_base(tmp_path, [claim(status="established", burden_profile="source_report")])
    assert validate(tmp_path) == []


def test_valid_meta_claim_established_no_ledger(tmp_path):
    """meta_claim is exempt as a case-constitutive local scope claim."""
    write_base(tmp_path, [claim(status="established", claim_type="meta_claim")])
    assert validate(tmp_path) == []


def test_valid_causal_chain_plausible_with_uncertainty_preservation(tmp_path):
    write_base(tmp_path, [claim(status="plausible", burden_profile="causal_chain")])
    s = step(operation="uncertainty_preservation", produces="Verdict is weak due to unresolvable quantification gap.")
    write_yaml(tmp_path / "inference-ledger.yml", ledger([inference(triggered_by="causal_chain", inference_steps=[s])]))
    assert validate(tmp_path) == []


def test_valid_high_materiality_defeater_treated(tmp_path):
    write_base(tmp_path, [claim(status="strongly_supported")])
    write_yaml(
        tmp_path / "model-defeaters.yml",
        {
            "schema_version": "1.0",
            "case_ref": "cases/test",
            "defeaters": [{
                "defeater_id": "d001",
                "target_claim_ref": "c001",
                "defeater_type": "central_data_gap",
                "statement": "Key data is missing.",
                "materiality": 0.8,
                "status": "unresolved",
                "rebuttal_evidence_refs": [],
                "verdict_effect": {"effect": "prevents_strong_closure", "rationale": ""},
            }],
        },
    )
    s = step(operation="defeater_response", produces="Addressed: data gap does not invalidate existing corroboration.")
    write_yaml(tmp_path / "inference-ledger.yml", ledger([inference(inference_steps=[s])]))
    assert validate(tmp_path) == []


# --- invalid cases ---

def test_invalid_established_without_ledger(tmp_path):
    write_base(tmp_path, [claim(status="established")])
    errors = validate(tmp_path)
    assert any("requires an inference-ledger entry" in e and "c001" in e for e in errors), errors


def test_invalid_contradicted_without_ledger(tmp_path):
    write_base(tmp_path, [claim(status="contradicted")])
    errors = validate(tmp_path)
    assert any("requires an inference-ledger entry" in e and "c001" in e for e in errors), errors


def test_invalid_unknown_claim_ref(tmp_path):
    write_base(tmp_path, [claim(status="strongly_supported")])
    write_yaml(tmp_path / "inference-ledger.yml", ledger([inference(claim_ref="c999")]))
    errors = validate(tmp_path)
    assert any("claim_ref 'c999' not found in claims.yml" in e for e in errors), errors


def test_invalid_unknown_evidence_ref(tmp_path):
    write_base(tmp_path, [claim(status="strongly_supported")])
    s = step(premise_evidence_refs=["e999"])
    write_yaml(tmp_path / "inference-ledger.yml", ledger([inference(inference_steps=[s])]))
    errors = validate(tmp_path)
    assert any("premise_evidence_ref 'e999' not found in evidence-pack.yml" in e for e in errors), errors


def test_invalid_duplicate_inference_id(tmp_path):
    write_base(tmp_path, [claim(status="strongly_supported")])
    inf1 = inference()
    inf2 = inference(inference_steps=[step(step_id="step002")])
    write_yaml(tmp_path / "inference-ledger.yml", ledger([inf1, inf2]))
    errors = validate(tmp_path)
    assert any("duplicate inference_id 'inf001'" in e for e in errors), errors


def test_invalid_causal_chain_plausible_without_ledger(tmp_path):
    write_base(tmp_path, [claim(status="plausible", burden_profile="causal_chain")])
    errors = validate(tmp_path)
    assert any("requires an inference-ledger entry" in e and "c001" in e for e in errors), errors


def test_invalid_unresolved_high_materiality_defeater_without_step(tmp_path):
    write_base(tmp_path, [claim(status="strongly_supported")])
    write_yaml(
        tmp_path / "model-defeaters.yml",
        {
            "schema_version": "1.0",
            "case_ref": "cases/test",
            "defeaters": [{
                "defeater_id": "d001",
                "target_claim_ref": "c001",
                "defeater_type": "central_data_gap",
                "statement": "Key data is missing.",
                "materiality": 0.8,
                "status": "unresolved",
                "rebuttal_evidence_refs": [],
                "verdict_effect": {"effect": "prevents_strong_closure", "rationale": ""},
            }],
        },
    )
    # Inference exists but only has corroboration — no defeater_response or uncertainty_preservation
    write_yaml(tmp_path / "inference-ledger.yml", ledger([inference()]))
    errors = validate(tmp_path)
    assert any(
        "defeater_response" in e and "uncertainty_preservation" in e and "d001" in e
        for e in errors
    ), errors
