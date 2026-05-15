"""Tests for scripts/validate_evidence_pack.py"""

import json
import pathlib
import sys

import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_evidence_pack

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "evidence-pack.v1.schema.json"


@pytest.fixture
def schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def base_evidence(**overrides) -> dict:
    e = {
        "evidence_id": "e001",
        "source_ref": "s001",
        "claim_refs": ["c001"],
        "type": "official_statement",
        "summary": "A valid summary.",
        "verbatim_or_ref": "See source s001.",
        "supports": ["c001"],
        "contradicts": [],
    }
    e.update(overrides)
    return e


def base_pack(evidence_items=None) -> dict:
    return {
        "schema_version": "1.0",
        "evidence": evidence_items if evidence_items is not None else [base_evidence()],
    }


def validate_pack(pack: dict, schema: dict) -> list[str]:
    from jsonschema_compat import jsonschema
    validator = jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())
    return [
        f"  Schema error at {list(e.absolute_path)}: {e.message}"
        for e in validator.iter_errors(pack)
    ]


def test_valid_evidence_pack_passes(schema):
    errors = validate_pack(base_pack(), schema)
    assert errors == [], f"Expected no errors, got: {errors}"


def test_evidence_audit_locator_fields_pass(schema):
    item = base_evidence(
        evidence_excerpt="Short stable excerpt or paraphrase.",
        locator="section 2, paragraph 4",
        accessed_at="2026-05-14",
        archive_url="https://web.archive.org/example",
        content_hash="sha256:example",
    )
    errors = validate_pack(base_pack([item]), schema)
    assert errors == [], f"Expected no errors, got: {errors}"


def test_invalid_evidence_id_fails(schema):
    errors = validate_pack(base_pack([base_evidence(evidence_id="bad")]), schema)
    assert len(errors) >= 1
    assert any("evidence_id" in e or "pattern" in e for e in errors)


def test_invalid_evidence_type_fails(schema):
    errors = validate_pack(base_pack([base_evidence(type="blog_post")]), schema)
    assert len(errors) >= 1
    assert any("blog_post" in e or "type" in e for e in errors)


def test_missing_source_ref_fails(schema):
    item = base_evidence()
    del item["source_ref"]
    errors = validate_pack(base_pack([item]), schema)
    assert len(errors) >= 1
    assert any("source_ref" in e for e in errors)


def test_additional_property_fails(schema):
    item = base_evidence()
    item["unexpected_field"] = "boom"
    errors = validate_pack(base_pack([item]), schema)
    assert len(errors) >= 1
    assert any("unexpected_field" in e or "Additional" in e for e in errors)
