"""Tests for scripts/validate_sources.py"""

import json
import pathlib
import sys

import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_sources

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "source.v1.schema.json"


@pytest.fixture
def schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def base_source(**overrides) -> dict:
    s = {
        "schema_version": "1.0",
        "source_id": "s001",
        "label": "Test Source",
        "url_or_ref": "https://example.org/test",
        "source_type": "official_body",
        "publication_date": "2026-01-01",
    }
    s.update(overrides)
    return s


def test_valid_source_passes(schema):
    errors = validate_sources.validate_source(base_source(), schema)
    assert errors == [], f"Expected no errors, got: {errors}"


def test_invalid_source_type_fails(schema):
    errors = validate_sources.validate_source(base_source(source_type="blog_post"), schema)
    assert len(errors) >= 1
    assert any("source_type" in e or "blog_post" in e for e in errors)


def test_invalid_publication_date_fails(schema):
    errors = validate_sources.validate_source(base_source(publication_date="not-a-date"), schema)
    assert len(errors) >= 1


def test_source_weight_above_1_fails(schema):
    errors = validate_sources.validate_source(
        base_source(source_weight={"primary_proximity": 1.5}), schema
    )
    assert len(errors) >= 1
    assert any("1.5" in e or "maximum" in e for e in errors)


def test_malformed_source_id_fails(schema):
    errors = validate_sources.validate_source(base_source(source_id="bad"), schema)
    assert len(errors) >= 1
    assert any("source_id" in e or "pattern" in e for e in errors)
