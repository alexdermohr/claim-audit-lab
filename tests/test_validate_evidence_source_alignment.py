"""Tests for scripts/validate_evidence_source_alignment.py"""

import pathlib
import sys
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_evidence_source_alignment


def _write_case(tmp_path, evidence_yaml):
    case_dir = tmp_path / "cases" / "sandbox" / "test-case"
    case_dir.mkdir(parents=True)
    (case_dir / "evidence-pack.yml").write_text(evidence_yaml, encoding="utf-8")
    # Minimal marker file for case discovery
    (case_dir / "evidence-relations.yml").write_text(
        "schema_version: '1.0'\nrelations: []\n", encoding="utf-8"
    )
    return case_dir


def _evidence_pack(evidence_list: list[dict]) -> str:
    data = {"schema_version": "1.0", "evidence": evidence_list}
    return yaml.dump(data, allow_unicode=True, default_flow_style=False)


def _minimal_evidence(evidence_id: str, source_ref: str, **text_fields) -> dict:
    ev = {
        "evidence_id": evidence_id,
        "source_ref": source_ref,
        "summary": "Summary.",
        "quality": "primary",
        "relevance": "direct",
    }
    ev.update(text_fields)
    return ev


# ---------- Fail tests ----------


def test_source_ref_mismatch_fails(tmp_path):
    """evidence_excerpt cites s001 via marker but source_ref is s005 → fail."""
    ev = _minimal_evidence(
        "e001",
        "s005",
        evidence_excerpt="Source position from s001: 'Original quote here.'",
    )
    _write_case(tmp_path, _evidence_pack([ev]))
    result = validate_evidence_source_alignment.main(str(tmp_path / "cases"))
    assert result == 1, "Expected failure: cited s001 but source_ref=s005"


def test_multiple_source_ids_in_one_record_fails(tmp_path):
    """A single evidence record citing 'from s001' and 'from s008' must fail."""
    ev = _minimal_evidence(
        "e002",
        "s001",
        evidence_excerpt="Quoted from s001: first quote.",
        notes="See also from s008: cross-reference note.",
    )
    _write_case(tmp_path, _evidence_pack([ev]))
    result = validate_evidence_source_alignment.main(str(tmp_path / "cases"))
    assert result == 1, "Expected failure: multiple source IDs in one record"


def test_error_message_includes_evidence_id_and_source_refs(tmp_path):
    """Error message must include evidence ID and the mismatch details."""
    from io import StringIO
    import contextlib

    ev = _minimal_evidence(
        "e007",
        "s005",
        evidence_excerpt="Source position from s001: 'quote'",
    )
    _write_case(tmp_path, _evidence_pack([ev]))

    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        result = validate_evidence_source_alignment.main(str(tmp_path / "cases"))

    assert result == 1
    output = buf.getvalue()
    assert "e007" in output
    assert "s001" in output
    assert "s005" in output


# ---------- Pass tests ----------


def test_matching_source_ref_passes(tmp_path):
    """evidence_excerpt cites s001 via marker and source_ref is s001 → pass."""
    ev = _minimal_evidence(
        "e001",
        "s001",
        evidence_excerpt="Source position from s001: 'Quote.'",
    )
    _write_case(tmp_path, _evidence_pack([ev]))
    result = validate_evidence_source_alignment.main(str(tmp_path / "cases"))
    assert result == 0, "Expected pass: source_ref matches citation marker"


def test_evidence_without_marker_passes(tmp_path):
    """Evidence with no explicit source-ID citation marker always passes."""
    ev = _minimal_evidence(
        "e003",
        "s004",
        evidence_excerpt="This document describes events in 1943.",
        notes="No source ID markers here.",
    )
    _write_case(tmp_path, _evidence_pack([ev]))
    result = validate_evidence_source_alignment.main(str(tmp_path / "cases"))
    assert result == 0, "Expected pass: no citation markers"


def test_quoted_from_matching_source_ref_passes(tmp_path):
    """'Quoted from s003' with source_ref: s003 → pass."""
    ev = _minimal_evidence(
        "e005",
        "s003",
        evidence_excerpt="Quoted from s003: 'The relevant text.'",
    )
    _write_case(tmp_path, _evidence_pack([ev]))
    result = validate_evidence_source_alignment.main(str(tmp_path / "cases"))
    assert result == 0, "Expected pass: Quoted from matches source_ref"


def test_bare_source_id_in_notes_without_marker_passes(tmp_path):
    """Bare source ID reference in notes without a citation marker does not fail."""
    ev = _minimal_evidence(
        "e006",
        "s001",
        evidence_excerpt="Source position from s001: 'Quote.'",
        notes="Weitere Informationen in s004 dokumentiert.",
    )
    _write_case(tmp_path, _evidence_pack([ev]))
    result = validate_evidence_source_alignment.main(str(tmp_path / "cases"))
    assert result == 0, "Expected pass: 'in s004 dokumentiert' is not a citation marker"
