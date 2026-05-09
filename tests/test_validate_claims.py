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
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def load_fixture(name):
    with open(FIXTURES_DIR / name) as f:
        data = yaml.safe_load(f)
    return data["claims"] if "claims" in data else [data]


def test_valid_claim_passes(schema):
    # Load valid_claim.yml directly (it's a single claim, not wrapped in claims:)
    with open(FIXTURES_DIR / "valid_claim.yml") as f:
        claim = yaml.safe_load(f)
    errors = validate_claims.validate_claim(claim, schema)
    assert errors == [], f"Expected no errors, got: {errors}"


def test_invalid_causal_claim_missing_counterclaims(schema):
    with open(FIXTURES_DIR / "invalid_claim.yml") as f:
        claim = yaml.safe_load(f)
    errors = validate_claims.validate_claim(claim, schema)
    # Should have errors: causal_claim without counterclaims, and strongly_supported without source_refs
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


def test_causal_claim_with_counterhypotheses_req_passes(schema):
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
    assert errors == [], f"Expected no errors, got: {errors}"


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
    assert len(errors) == 2
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
        "evidence_refs": [],
        "source_refs": [],
        "requires": ["timeline"],
        "counterclaims": [],
        "forbidden_upgrades": [],
        "uncertainty": {"score": 0.0, "causes": []},
        "interpolation": {"score": 0.0, "assumptions": []},
    }
    errors = validate_claims.validate_claim(claim, schema)
    assert len(errors) >= 1
    assert any("strongly_supported" in e for e in errors)
