"""Tests for scripts/validate_claims.py"""

import pathlib
import json
import pytest
import yaml

# Add scripts dir to path
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_claims

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"
SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "claim.v1.schema.json"


@pytest.fixture
def schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_valid_claim_passes(schema):
    with open(FIXTURES_DIR / "valid_claim.yml", encoding="utf-8") as f:
        claim = yaml.safe_load(f)
    errors = validate_claims.validate_claim(claim, schema)
    assert errors == [], f"Expected no errors, got: {errors}"


def test_invalid_causal_claim_missing_counterclaims(schema):
    with open(FIXTURES_DIR / "invalid_claim.yml", encoding="utf-8") as f:
        claim = yaml.safe_load(f)
    errors = validate_claims.validate_claim(claim, schema)
    assert len(errors) >= 1
    assert any("causal_claim" in e for e in errors)


def test_causal_claim_with_counterclaims_passes(schema):
    claim = {
        "schema_version": "1.0",
        "claim_id": "c010",
        "claim_type": "causal_claim",
        "statement": "A caused B.",
        "status": "plausible",
        "evidence_refs": ["e001"],
        "source_refs": ["s001"],
        "requires": ["timeline", "mechanism"],
        "counterclaims": ["c011", "c012"],
        "forbidden_upgrades": ["correlation_to_causation"],
        "uncertainty": {"score": 0.4, "causes": ["limited evidence"]},
        "interpolation": {"score": 0.2, "assumptions": ["mechanism assumed"]},
    }
    errors = validate_claims.validate_claim(claim, schema)
    assert errors == [], f"Expected no errors, got: {errors}"


def test_causal_claim_with_counterhypotheses_only_fails(schema):
    claim = {
        "schema_version": "1.0",
        "claim_id": "c011",
        "claim_type": "causal_claim",
        "statement": "A caused B.",
        "status": "plausible",
        "evidence_refs": [],
        "source_refs": [],
        "requires": ["timeline", "counterhypotheses"],
        "counterclaims": [],
        "forbidden_upgrades": ["correlation_to_causation"],
        "uncertainty": {"score": 0.5, "causes": []},
        "interpolation": {"score": 0.3, "assumptions": []},
    }
    errors = validate_claims.validate_claim(claim, schema)
    assert any("causal_claim" in e for e in errors)


def test_motive_claim_missing_capability_and_interest(schema):
    claim = {
        "schema_version": "1.0",
        "claim_id": "c020",
        "claim_type": "motive_claim",
        "statement": "Actor X intended Y.",
        "status": "speculative",
        "evidence_refs": [],
        "source_refs": [],
        "requires": ["timeline"],
        "counterclaims": [],
        "forbidden_upgrades": ["benefit_to_motive"],
        "uncertainty": {"score": 0.8, "causes": []},
        "interpolation": {"score": 0.5, "assumptions": []},
    }
    errors = validate_claims.validate_claim(claim, schema)
    assert len(errors) >= 2
    assert any("capability" in e for e in errors)
    assert any("interest" in e for e in errors)


def test_statistical_claim_missing_method(schema):
    claim = {
        "schema_version": "1.0",
        "claim_id": "c030",
        "claim_type": "statistical_claim",
        "statement": "42% of respondents agreed.",
        "status": "plausible",
        "evidence_refs": [],
        "source_refs": ["s001"],
        "requires": ["sample"],
        "counterclaims": [],
        "forbidden_upgrades": ["correlation_to_causation"],
        "uncertainty": {"score": 0.3, "causes": []},
        "interpolation": {"score": 0.1, "assumptions": []},
    }
    errors = validate_claims.validate_claim(claim, schema)
    assert len(errors) >= 1
    assert any("method" in e or "dataset" in e for e in errors)


def test_strongly_supported_without_sources_fails(schema):
    claim = {
        "schema_version": "1.0",
        "claim_id": "c040",
        "claim_type": "factual_event_claim",
        "statement": "Event occurred.",
        "status": "strongly_supported",
        "evidence_refs": ["e001"],
        "source_refs": [],
        "requires": ["timeline"],
        "counterclaims": [],
        "forbidden_upgrades": [],
        "uncertainty": {"score": 0.0, "causes": []},
        "interpolation": {"score": 0.0, "assumptions": []},
    }
    errors = validate_claims.validate_claim(claim, schema)
    assert any("source_refs" in e for e in errors)


def test_established_without_evidence_refs_fails(schema):
    claim = {
        "schema_version": "1.0",
        "claim_id": "c041",
        "claim_type": "factual_event_claim",
        "statement": "Event occurred.",
        "status": "established",
        "evidence_refs": [],
        "source_refs": ["s001"],
        "requires": ["timeline"],
        "counterclaims": [],
        "forbidden_upgrades": [],
        "uncertainty": {"score": 0.0, "causes": []},
        "interpolation": {"score": 0.0, "assumptions": []},
    }
    errors = validate_claims.validate_claim(claim, schema)
    assert any("evidence_refs" in e for e in errors)


def test_reported_claim_requires_source_report_burden_profile(schema):
    claim = {
        "schema_version": "1.0",
        "claim_id": "c050",
        "claim_type": "meta_claim",
        "claim_kind": "reported_claim",
        "statement": "Source X reports Y.",
        "status": "established",
        "evidence_refs": ["e001"],
        "source_refs": ["s001"],
        "requires": ["source content"],
        "counterclaims": [],
        "forbidden_upgrades": ["source_prestige_to_truth"],
        "uncertainty": {"score": 0.1, "causes": []},
        "interpolation": {"score": 0.0, "assumptions": []},
    }
    errors = validate_claims.validate_claim(claim, schema)
    assert any("burden_profile='source_report'" in e for e in errors), errors


def test_absence_claim_without_scope_fails(schema):
    claim = {
        "schema_version": "1.0",
        "claim_id": "c051",
        "claim_type": "meta_claim",
        "claim_kind": "absence_claim",
        "statement": "No record exists.",
        "status": "plausible",
        "evidence_refs": [],
        "source_refs": [],
        "requires": [],
        "counterclaims": [],
        "forbidden_upgrades": ["absence_of_evidence_to_falsehood"],
        "uncertainty": {"score": 0.4, "causes": []},
        "interpolation": {"score": 0.2, "assumptions": []},
    }
    errors = validate_claims.validate_claim(claim, schema)
    assert any("bounded scope" in e for e in errors), errors


def test_absence_claim_with_evidence_pack_scope_and_forbidden_upgrade_passes(schema):
    claim = {
        "schema_version": "1.0",
        "claim_id": "c052",
        "claim_type": "meta_claim",
        "claim_kind": "absence_claim",
        "absence_scope": "im vorliegenden Evidence-Pack",
        "statement": "Im vorliegenden Evidence-Pack liegt kein direkter Beleg für X vor.",
        "status": "plausible",
        "evidence_refs": ["e001"],
        "source_refs": ["s001"],
        "requires": ["reviewed evidence-pack scope"],
        "counterclaims": [],
        "forbidden_upgrades": ["absence_of_evidence_to_falsehood"],
        "uncertainty": {"score": 0.4, "causes": []},
        "interpolation": {"score": 0.2, "assumptions": []},
    }
    errors = validate_claims.validate_claim(claim, schema)
    assert errors == []


def test_absence_claim_requires_forbidden_upgrade(schema):
    claim = {
        "schema_version": "1.0",
        "claim_id": "c053",
        "claim_type": "meta_claim",
        "claim_kind": "absence_claim",
        "absence_scope": "in dataset Y",
        "statement": "No matching row appears in dataset Y.",
        "status": "plausible",
        "evidence_refs": [],
        "source_refs": [],
        "requires": [],
        "counterclaims": [],
        "forbidden_upgrades": [],
        "uncertainty": {"score": 0.4, "causes": []},
        "interpolation": {"score": 0.2, "assumptions": []},
    }
    errors = validate_claims.validate_claim(claim, schema)
    assert any("absence_of_evidence_to_falsehood" in e for e in errors), errors


def test_co_causation_claim_is_not_automatically_contradicted_by_alternative_explanation(schema):
    claim = {
        "schema_version": "1.0",
        "claim_id": "c054",
        "claim_type": "causal_claim",
        "claim_kind": "causal_claim",
        "statement": "A contributed to B alongside other causes.",
        "status": "weak",
        "evidence_refs": ["e001"],
        "source_refs": ["s001"],
        "requires": ["timeline", "mechanism"],
        "counterclaims": ["Alternative explanation one.", "Alternative explanation two."],
        "forbidden_upgrades": ["correlation_to_causation"],
        "uncertainty": {"score": 0.4, "causes": []},
        "interpolation": {"score": 0.2, "assumptions": []},
        "notes": "A stronger primary explanation exists, but direct incompatibility has not been documented.",
    }
    errors = validate_claims.validate_claim(claim, schema)
    assert errors == []


def test_co_causation_contradicted_requires_direct_incompatibility_basis(schema):
    claim = {
        "schema_version": "1.0",
        "claim_id": "c055",
        "claim_type": "causal_claim",
        "claim_kind": "causal_claim",
        "statement": "A contributed to B alongside other causes.",
        "status": "contradicted",
        "evidence_refs": ["e001"],
        "source_refs": ["s001"],
        "requires": ["timeline", "mechanism"],
        "counterclaims": ["Alternative explanation one.", "Alternative explanation two."],
        "forbidden_upgrades": ["correlation_to_causation"],
        "uncertainty": {"score": 0.4, "causes": []},
        "interpolation": {"score": 0.2, "assumptions": []},
        "notes": "A stronger primary explanation exists.",
    }
    errors = validate_claims.validate_claim(claim, schema)
    assert any("direct_incompatibility_basis" in e for e in errors), errors


def test_co_causation_contradicted_with_direct_incompatibility_basis_passes(schema):
    claim = {
        "schema_version": "1.0",
        "claim_id": "c056",
        "claim_type": "causal_claim",
        "claim_kind": "causal_claim",
        "statement": "A contributed to B alongside other causes.",
        "status": "contradicted",
        "evidence_refs": ["e001"],
        "source_refs": ["s001"],
        "requires": ["timeline", "mechanism"],
        "counterclaims": ["Alternative explanation one.", "Alternative explanation two."],
        "forbidden_upgrades": ["correlation_to_causation"],
        "uncertainty": {"score": 0.4, "causes": []},
        "interpolation": {"score": 0.2, "assumptions": []},
        "direct_incompatibility_basis": "Evidence directly rules out A as a contributing cause under the claim scope.",
    }
    errors = validate_claims.validate_claim(claim, schema)
    assert errors == []


def test_co_causation_negated_notes_do_not_satisfy_direct_incompatibility_basis(schema):
    claim = {
        "schema_version": "1.0",
        "claim_id": "c057",
        "claim_type": "causal_claim",
        "claim_kind": "causal_claim",
        "statement": "A contributed to B alongside other causes.",
        "status": "contradicted",
        "evidence_refs": ["e001"],
        "source_refs": ["s001"],
        "requires": ["timeline", "mechanism"],
        "counterclaims": ["Alternative explanation one.", "Alternative explanation two."],
        "forbidden_upgrades": ["correlation_to_causation"],
        "uncertainty": {"score": 0.4, "causes": []},
        "interpolation": {"score": 0.2, "assumptions": []},
        "notes": "A stronger primary explanation exists, but direct incompatibility has not been documented.",
    }
    errors = validate_claims.validate_claim(claim, schema)
    assert any("direct_incompatibility_basis" in e for e in errors), errors


def test_malformed_claims_yaml_reports_clean_error(tmp_path, capsys):
    claims_file = tmp_path / "claims.yml"
    claims_file.write_text("schema_version: [\n", encoding="utf-8")
    errors = validate_claims.validate_file(claims_file, validate_claims.load_schema())
    captured = capsys.readouterr()
    assert errors == 1
    assert "Could not parse YAML" in captured.out
    assert "Traceback" not in captured.out
