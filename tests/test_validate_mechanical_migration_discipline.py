"""Tests for scripts/validate_mechanical_migration_discipline.py."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_mechanical_migration_discipline


def write_relations(path, relation_type="supports_indirectly", strength=0.5):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'''schema_version: "1.0"
case_ref: "tests/fixtures"
relations:
  - relation_id: "r001"
    evidence_ref: "e001"
    claim_ref: "c001"
    relation_type: "{relation_type}"
    strength: {strength}
    explanation: "Mechanical migration from existing legacy evidence-pack edge; not a semantic upgrade. Pending full semantic audit."
''',
        encoding="utf-8",
    )


def test_mechanical_migration_supports_directly_fails(tmp_path):
    path = tmp_path / "cases" / "case-a" / "evidence-relations.yml"
    write_relations(path, relation_type="supports_directly", strength=0.5)
    errors = validate_mechanical_migration_discipline.validate(tmp_path / "cases")
    assert any("supports_directly" in e for e in errors), errors


def test_mechanical_migration_strength_above_cap_fails(tmp_path):
    path = tmp_path / "cases" / "case-a" / "evidence-relations.yml"
    write_relations(path, relation_type="supports_indirectly", strength=0.7)
    errors = validate_mechanical_migration_discipline.validate(tmp_path / "cases")
    assert any("strength must be <=" in e for e in errors), errors


def test_mechanical_migration_indirect_with_conservative_strength_passes(tmp_path):
    path = tmp_path / "cases" / "case-a" / "evidence-relations.yml"
    write_relations(path, relation_type="supports_indirectly", strength=0.5)
    assert validate_mechanical_migration_discipline.validate(tmp_path / "cases") == []
