"""Tests for scripts/validate_no_fixture_language.py."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_no_fixture_language


def test_production_case_with_fixture_relation_fails(tmp_path):
    path = tmp_path / "cases" / "history" / "case-a" / "evidence-relations.yml"
    path.parent.mkdir(parents=True)
    path.write_text('explanation: "Fixture relation"\n', encoding="utf-8")
    errors = validate_no_fixture_language.validate(tmp_path / "cases")
    assert any("forbidden fixture/test language" in e and str(path) in e for e in errors), errors


def test_sandbox_fixture_language_passes(tmp_path):
    path = tmp_path / "cases" / "sandbox" / "case-a" / "sources.yml"
    path.parent.mkdir(parents=True)
    path.write_text('label: "Fixture source"\n', encoding="utf-8")
    assert validate_no_fixture_language.validate(tmp_path / "cases") == []


def test_template_placeholder_language_passes(tmp_path):
    path = tmp_path / "cases" / "_template" / "question.md"
    path.parent.mkdir(parents=True)
    path.write_text("[placeholder text]\n", encoding="utf-8")
    assert validate_no_fixture_language.validate(tmp_path / "cases") == []


def test_cli_returns_nonzero_and_prints_offending_path(tmp_path, capsys):
    path = tmp_path / "cases" / "history" / "case-a" / "assessment.md"
    path.parent.mkdir(parents=True)
    path.write_text("Synthetic assessment text.\n", encoding="utf-8")
    exit_code = validate_no_fixture_language.main(str(tmp_path / "cases"))
    captured = capsys.readouterr()
    assert exit_code == 1
    assert str(path) in captured.out
    assert "synthetic" in captured.out.lower()


def test_nested_sandbox_name_in_production_path_fails(tmp_path):
    path = tmp_path / "cases" / "history" / "sandbox" / "case-a" / "sources.yml"
    path.parent.mkdir(parents=True)
    path.write_text('label: "Fixture source"\n', encoding="utf-8")
    errors = validate_no_fixture_language.validate(tmp_path / "cases")
    assert any(str(path) in e for e in errors), errors
