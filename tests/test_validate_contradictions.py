"""Tests for scripts/validate_contradictions.py"""

import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_contradictions

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "contradictions.v1.schema.json"


def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def write_yaml(path: pathlib.Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def claims(counterclaims=None):
    return {
        "schema_version": "1.0",
        "claims": [
            {
                "schema_version": "1.0",
                "claim_id": "c001",
                "claim_type": "factual_event_claim",
                "statement": "Claim one.",
                "status": "plausible",
                "evidence_refs": [],
                "source_refs": [],
                "counterclaims": counterclaims or [],
                "uncertainty": {"score": 0.5, "causes": []},
                "interpolation": {"score": 0.2, "assumptions": []},
            },
            {
                "schema_version": "1.0",
                "claim_id": "c002",
                "claim_type": "factual_event_claim",
                "statement": "Claim two.",
                "status": "plausible",
                "evidence_refs": [],
                "source_refs": [],
                "counterclaims": [],
                "uncertainty": {"score": 0.5, "causes": []},
                "interpolation": {"score": 0.2, "assumptions": []},
            },
        ],
    }


def lifecycle(status="provisional_under_uncertainty"):
    return {
        "schema_version": "1.0",
        "assessment_id": "a001",
        "case_ref": "cases/test",
        "status": status,
        "created_at": "2026-05-16",
        "last_reviewed_at": "2026-05-16",
        "review_after": "2026-08-16",
        "redteam_ref": "redteam.yml",
        "reopen_triggers": ["major_contradiction"],
        "history": [{"date": "2026-05-16", "status": status, "note": "Fixture."}],
    }


def contradictions(**overrides):
    item = {
        "contradiction_id": "con001",
        "claim_a_ref": "c001",
        "claim_b_ref": "c002",
        "description": "Claims conflict under scope S.",
        "resolution_status": "weighted_only",
        "resolution_notes": "Conflict is weighted, not erased.",
    }
    item.update(overrides)
    return {"schema_version": "1.0", "contradictions": [item]}


def test_counterclaims_in_provisional_case_require_contradictions_ledger(tmp_path):
    write_yaml(tmp_path / "claims.yml", claims(counterclaims=["Counterclaim text."]))
    write_yaml(tmp_path / "lifecycle.yml", lifecycle())
    errors = validate_contradictions.validate_case(tmp_path, load_schema())
    assert any("contradictions.yml required" in e for e in errors), errors


def test_draft_counterclaims_do_not_block_without_contradictions_ledger(tmp_path):
    write_yaml(tmp_path / "claims.yml", claims(counterclaims=["Counterclaim text."]))
    write_yaml(tmp_path / "lifecycle.yml", lifecycle(status="draft"))
    errors = validate_contradictions.validate_case(tmp_path, load_schema())
    assert errors == []


def test_contradiction_references_must_exist(tmp_path):
    write_yaml(tmp_path / "claims.yml", claims())
    write_yaml(tmp_path / "lifecycle.yml", lifecycle())
    write_yaml(tmp_path / "contradictions.yml", contradictions(claim_b_ref="c999"))
    errors = validate_contradictions.validate_case(tmp_path, load_schema())
    assert any("not found in claims.yml" in e for e in errors), errors


def test_contradiction_requires_resolution_notes(tmp_path):
    write_yaml(tmp_path / "claims.yml", claims())
    write_yaml(tmp_path / "lifecycle.yml", lifecycle())
    write_yaml(tmp_path / "contradictions.yml", contradictions(resolution_notes=""))
    errors = validate_contradictions.validate_case(tmp_path, load_schema())
    assert any("resolution_notes" in e for e in errors), errors


def test_malformed_contradictions_yaml_reports_clean_error(tmp_path):
    write_yaml(tmp_path / "claims.yml", claims())
    write_yaml(tmp_path / "lifecycle.yml", lifecycle())
    (tmp_path / "contradictions.yml").write_text("schema_version: [\n", encoding="utf-8")
    errors = validate_contradictions.validate_case(tmp_path, load_schema())
    assert any("Could not parse contradictions.yml" in e for e in errors), errors
    assert not any("Traceback" in e for e in errors)


def test_contradictions_schema_allows_optional_case_ref(tmp_path):
    write_yaml(tmp_path / "claims.yml", claims())
    write_yaml(tmp_path / "lifecycle.yml", lifecycle())
    payload = contradictions()
    payload["case_ref"] = "cases/test"
    write_yaml(tmp_path / "contradictions.yml", payload)
    errors = validate_contradictions.validate_case(tmp_path, load_schema())
    assert errors == []
