"""Tests for scripts/validate_absence_language_scope.py"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_absence_language_scope


def _write_case(tmp_path, claims_yaml):
    case_dir = tmp_path / "cases" / "sandbox" / "test-case"
    case_dir.mkdir(parents=True)
    (case_dir / "claims.yml").write_text(claims_yaml, encoding="utf-8")
    # Minimal marker files for case discovery
    (case_dir / "evidence-relations.yml").write_text("schema_version: '1.0'\nrelations: []\n", encoding="utf-8")
    return case_dir


def _minimal_claim(**overrides) -> dict:
    base = {
        "schema_version": "1.0",
        "claim_id": "c001",
        "claim_type": "factual_event_claim",
        "statement": "X geschah.",
        "status": "weak",
        "uncertainty": {"score": 0.3, "causes": ["limited evidence"]},
        "interpolation": {"score": 0.1, "assumptions": ["assumption"]},
    }
    base.update(overrides)
    return base


def _dump_claims(*claims) -> str:
    import yaml
    return "schema_version: '1.0'\nclaims:\n" + "\n".join(
        "  - " + yaml.dump(c, allow_unicode=True, default_flow_style=False).replace("\n", "\n    ").rstrip("    ")
        for c in claims
    )


# ---------- Fail tests ----------


def test_absence_trigger_without_claim_kind_fails(tmp_path):
    """Claim with absence language but no claim_kind: absence_claim must fail."""
    claim = _minimal_claim(
        claim_id="c001",
        statement="Die Verbindung wurde nicht nachgewiesen.",
        status="weak",
    )
    claims_yaml = _dump_claims(claim)
    _write_case(tmp_path, claims_yaml)
    result = validate_absence_language_scope.main(str(tmp_path / "cases"))
    assert result == 1, "Expected failure: absence trigger without claim_kind"


def test_absence_claim_wrong_kind_fails(tmp_path):
    """claim_kind: causal_claim with absence trigger must fail."""
    claim = _minimal_claim(
        claim_id="c001",
        claim_kind="causal_claim",
        statement="No evidence of coordination.",
        status="weak",
    )
    claims_yaml = _dump_claims(claim)
    _write_case(tmp_path, claims_yaml)
    result = validate_absence_language_scope.main(str(tmp_path / "cases"))
    assert result == 1, "Expected failure: absence trigger with wrong claim_kind"


def test_absence_claim_established_without_exhaustivity_fails(tmp_path):
    """absence_claim with status: established but no exhaustivity marker must fail."""
    claim = _minimal_claim(
        claim_id="c001",
        claim_kind="absence_claim",
        statement="No evidence of X.",
        status="established",
        absence_scope="im vorliegenden Evidence-Pack",
        forbidden_upgrades=["absence_of_evidence_to_falsehood"],
        evidence_refs=[],
    )
    claims_yaml = _dump_claims(claim)
    _write_case(tmp_path, claims_yaml)
    result = validate_absence_language_scope.main(str(tmp_path / "cases"))
    assert result == 1, "Expected failure: established absence_claim without exhaustivity"


def test_absence_claim_missing_scope_fails(tmp_path):
    """absence_claim without absence_scope must fail."""
    claim = _minimal_claim(
        claim_id="c001",
        claim_kind="absence_claim",
        statement="kein nachweis gefunden.",
        status="weak",
        forbidden_upgrades=["absence_of_evidence_to_falsehood"],
    )
    claims_yaml = _dump_claims(claim)
    _write_case(tmp_path, claims_yaml)
    result = validate_absence_language_scope.main(str(tmp_path / "cases"))
    assert result == 1, "Expected failure: absence_claim without absence_scope"


# ---------- Pass tests ----------


def test_well_formed_absence_claim_passes(tmp_path):
    """Properly formed absence_claim with scope and forbidden upgrade passes."""
    claim = _minimal_claim(
        claim_id="c001",
        claim_kind="absence_claim",
        statement="No evidence of X.",
        status="weak",
        absence_scope="im vorliegenden Evidence-Pack",
        forbidden_upgrades=["absence_of_evidence_to_falsehood"],
    )
    claims_yaml = _dump_claims(claim)
    _write_case(tmp_path, claims_yaml)
    result = validate_absence_language_scope.main(str(tmp_path / "cases"))
    assert result == 0, "Expected pass: well-formed absence_claim"


def test_absence_claim_established_with_exhaustivity_passes(tmp_path):
    """absence_claim with established status, exhaustivity marker, and evidence_refs passes."""
    claim = _minimal_claim(
        claim_id="c001",
        claim_kind="absence_claim",
        statement="No evidence of X.",
        status="established",
        absence_scope="exhaustive search in dataset X covering all records 1939-1945",
        forbidden_upgrades=["absence_of_evidence_to_falsehood"],
        evidence_refs=["e001"],
    )
    claims_yaml = _dump_claims(claim)
    _write_case(tmp_path, claims_yaml)
    result = validate_absence_language_scope.main(str(tmp_path / "cases"))
    assert result == 0, "Expected pass: absence_claim with exhaustivity and evidence_refs"


def test_claim_without_absence_language_ignored(tmp_path):
    """A claim with no absence-language trigger is not checked and passes."""
    claim = _minimal_claim(
        claim_id="c001",
        statement="Die Verbindung ist gut dokumentiert.",
        status="strongly_supported",
    )
    claims_yaml = _dump_claims(claim)
    _write_case(tmp_path, claims_yaml)
    result = validate_absence_language_scope.main(str(tmp_path / "cases"))
    assert result == 0, "Expected pass: no absence language in statement"


def test_not_found_error_label_does_not_trigger_absence(tmp_path):
    """'Not Found' as an error label in a non-absence context must not trigger the validator."""
    claim = _minimal_claim(
        claim_id="c001",
        statement="The source title contains 'Not Found' as an HTTP error label.",
        status="weak",
    )
    claims_yaml = _dump_claims(claim)
    _write_case(tmp_path, claims_yaml)
    result = validate_absence_language_scope.main(str(tmp_path / "cases"))
    assert result == 0, "Expected pass: 'Not Found' bare string no longer triggers absence check"


def test_error_message_includes_claim_id_and_field(tmp_path):
    """Error messages must include the claim ID and violated field."""
    from io import StringIO
    import contextlib

    claim = _minimal_claim(
        claim_id="c042",
        statement="Es gibt keine Hinweise auf eine Koordinierung.",
    )
    claims_yaml = _dump_claims(claim)
    _write_case(tmp_path, claims_yaml)

    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        result = validate_absence_language_scope.main(str(tmp_path / "cases"))

    assert result == 1
    output = buf.getvalue()
    assert "c042" in output
    assert "claim_kind" in output
