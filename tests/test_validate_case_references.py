"""Tests for scripts/validate_case_references.py"""

import pathlib
import sys

import pytest
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_case_references

MINIMAL_CASE = pathlib.Path(__file__).parent.parent / "cases" / "sandbox" / "minimal-valid-case"


def write_yaml(path: pathlib.Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def write_text(path: pathlib.Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def base_claims(claim_id="c001", status="plausible", source_refs=None, evidence_refs=None) -> dict:
    return {
        "schema_version": "1.0",
        "claims": [{
            "claim_id": claim_id,
            "claim_type": "factual_event_claim",
            "statement": "Something happened.",
            "status": status,
            "source_refs": source_refs if source_refs is not None else [],
            "evidence_refs": evidence_refs if evidence_refs is not None else [],
            "requires": [],
            "counterclaims": [],
            "forbidden_upgrades": [],
            "uncertainty": {"score": 0.3, "causes": []},
            "interpolation": {"score": 0.1, "assumptions": []},
        }],
    }


def base_sources(source_id="s001") -> dict:
    return {
        "schema_version": "1.0",
        "sources": [{
            "source_id": source_id,
            "label": "Test source",
            "url_or_ref": "https://example.org",
            "source_type": "official_body",
            "schema_version": "1.0",
        }],
    }


def base_evidence_pack(evidence_id="e001", source_ref="s001", claim_refs=None, supports=None) -> dict:
    return {
        "schema_version": "1.0",
        "evidence": [{
            "evidence_id": evidence_id,
            "source_ref": source_ref,
            "claim_refs": claim_refs if claim_refs is not None else ["c001"],
            "type": "official_statement",
            "summary": "Test summary.",
            "verbatim_or_ref": "See source.",
            "supports": supports if supports is not None else ["c001"],
            "contradicts": [],
        }],
    }


def base_lifecycle(redteam_ref="redteam.yml") -> dict:
    return {
        "schema_version": "1.0",
        "assessment_id": "a001",
        "case_ref": "cases/test",
        "status": "draft",
        "created_at": "2026-05-09",
        "last_reviewed_at": "2026-05-09",
        "review_after": "2026-08-09",
        "redteam_ref": redteam_ref,
        "reopen_triggers": ["new_primary_source"],
        "history": [{"date": "2026-05-09", "status": "draft", "note": "opened"}],
    }


def base_redteam(assessment_ref: str) -> dict:
    return {
        "schema_version": "1.0",
        "review_id": "rt001",
        "assessment_ref": assessment_ref,
        "reviewer": "qa",
        "reviewed_at": "2026-05-09",
        "findings": [],
        "verdict": {"status": "pending"},
    }


# --- claim.source_refs tests ---

def test_claim_source_ref_to_missing_source_fails(tmp_path):
    write_yaml(tmp_path / "claims.yml", base_claims(source_refs=["s999"]))
    write_yaml(tmp_path / "sources.yml", base_sources("s001"))
    errors = validate_case_references.validate_case(tmp_path)
    assert any("s999" in e for e in errors), errors


def test_claim_evidence_ref_to_missing_evidence_fails(tmp_path):
    write_yaml(tmp_path / "claims.yml", base_claims(evidence_refs=["e999"]))
    write_yaml(tmp_path / "sources.yml", base_sources())
    write_yaml(tmp_path / "evidence-pack.yml", base_evidence_pack("e001"))
    errors = validate_case_references.validate_case(tmp_path)
    assert any("e999" in e for e in errors), errors


def test_evidence_source_ref_to_missing_source_fails(tmp_path):
    write_yaml(tmp_path / "claims.yml", base_claims())
    write_yaml(tmp_path / "sources.yml", base_sources("s001"))
    write_yaml(tmp_path / "evidence-pack.yml", base_evidence_pack(source_ref="s999"))
    errors = validate_case_references.validate_case(tmp_path)
    assert any("s999" in e for e in errors), errors


def test_evidence_claim_refs_to_missing_claim_fails(tmp_path):
    write_yaml(tmp_path / "claims.yml", base_claims("c001"))
    write_yaml(tmp_path / "sources.yml", base_sources())
    write_yaml(tmp_path / "evidence-pack.yml", base_evidence_pack(claim_refs=["c999"]))
    errors = validate_case_references.validate_case(tmp_path)
    assert any("c999" in e for e in errors), errors


def test_evidence_supports_to_missing_claim_fails(tmp_path):
    write_yaml(tmp_path / "claims.yml", base_claims("c001"))
    write_yaml(tmp_path / "sources.yml", base_sources())
    write_yaml(tmp_path / "evidence-pack.yml", base_evidence_pack(supports=["c999"]))
    errors = validate_case_references.validate_case(tmp_path)
    assert any("c999" in e for e in errors), errors


def test_evidence_contradicts_to_missing_claim_fails(tmp_path):
    pack = base_evidence_pack()
    pack["evidence"][0]["contradicts"] = ["c999"]
    pack["evidence"][0]["supports"] = []
    write_yaml(tmp_path / "claims.yml", base_claims("c001"))
    write_yaml(tmp_path / "sources.yml", base_sources())
    write_yaml(tmp_path / "evidence-pack.yml", pack)
    errors = validate_case_references.validate_case(tmp_path)
    assert any("c999" in e for e in errors), errors


# --- strong status tests ---

def test_established_claim_without_evidence_refs_fails(tmp_path):
    write_yaml(tmp_path / "claims.yml", base_claims(status="established", source_refs=["s001"], evidence_refs=[]))
    write_yaml(tmp_path / "sources.yml", base_sources())
    errors = validate_case_references.validate_case(tmp_path)
    assert any("evidence_refs" in e for e in errors), errors


def test_strongly_supported_claim_without_source_refs_fails(tmp_path):
    write_yaml(tmp_path / "claims.yml", base_claims(status="strongly_supported", source_refs=[], evidence_refs=["e001"]))
    write_yaml(tmp_path / "sources.yml", base_sources())
    write_yaml(tmp_path / "evidence-pack.yml", base_evidence_pack())
    errors = validate_case_references.validate_case(tmp_path)
    assert any("source_refs" in e for e in errors), errors


# --- plausible claim with empty refs passes ---

def test_plausible_claim_with_empty_refs_passes(tmp_path):
    write_yaml(tmp_path / "claims.yml", base_claims(status="plausible", source_refs=[], evidence_refs=[]))
    errors = validate_case_references.validate_case(tmp_path)
    assert errors == [], errors


# --- lifecycle and redteam file reference tests ---

def test_lifecycle_redteam_ref_missing_file_fails(tmp_path):
    write_yaml(tmp_path / "claims.yml", base_claims())
    write_yaml(tmp_path / "lifecycle.yml", base_lifecycle(redteam_ref="nonexistent.yml"))
    errors = validate_case_references.validate_case(tmp_path)
    assert any("nonexistent.yml" in e for e in errors), errors


def test_redteam_assessment_ref_missing_file_fails(tmp_path):
    write_yaml(tmp_path / "claims.yml", base_claims())
    write_yaml(tmp_path / "lifecycle.yml", base_lifecycle())
    write_text(tmp_path / "redteam.yml")
    # Write redteam with assessment_ref pointing to missing file
    write_yaml(tmp_path / "redteam.yml", base_redteam("no/such/assessment.md"))
    errors = validate_case_references.validate_case(tmp_path)
    assert any("assessment" in e.lower() for e in errors), errors


# --- custom redteam_ref honoured ---

def test_custom_redteam_ref_with_missing_assessment_fails(tmp_path):
    """lifecycle.redteam_ref points to custom-redteam.yml; its assessment_ref is missing."""
    write_yaml(tmp_path / "claims.yml", base_claims())
    write_yaml(tmp_path / "lifecycle.yml", base_lifecycle(redteam_ref="custom-redteam.yml"))
    write_yaml(tmp_path / "custom-redteam.yml", base_redteam("no/such/assessment.md"))
    errors = validate_case_references.validate_case(tmp_path)
    assert any("assessment" in e.lower() for e in errors), errors


def test_custom_redteam_ref_ignores_stale_default(tmp_path):
    """lifecycle.redteam_ref points to custom-redteam.yml with a missing assessment.
    A stale redteam.yml with a valid assessment also exists.
    The validator must use custom-redteam.yml and report the missing assessment."""
    write_yaml(tmp_path / "claims.yml", base_claims())
    write_yaml(tmp_path / "lifecycle.yml", base_lifecycle(redteam_ref="custom-redteam.yml"))
    # stale default with a valid assessment file present
    write_text(tmp_path / "real-assessment.md", "valid assessment")
    write_yaml(tmp_path / "redteam.yml", base_redteam(str(tmp_path / "real-assessment.md")))
    # custom file points to a missing assessment
    write_yaml(tmp_path / "custom-redteam.yml", base_redteam("no/such/assessment.md"))
    errors = validate_case_references.validate_case(tmp_path)
    assert any("assessment" in e.lower() for e in errors), (
        "Validator did not use lifecycle.redteam_ref; it fell back to stale redteam.yml"
    )


# --- malformed YAML produces controlled error, no traceback ---

def test_malformed_claims_yaml_returns_error(tmp_path):
    (tmp_path / "claims.yml").write_text(": bad: yaml: [\n", encoding="utf-8")
    errors = validate_case_references.validate_case(tmp_path)
    assert any("claims.yml" in e and "parse" in e.lower() for e in errors), errors


def test_malformed_redteam_yaml_returns_error(tmp_path):
    write_yaml(tmp_path / "claims.yml", base_claims())
    write_yaml(tmp_path / "lifecycle.yml", base_lifecycle())
    (tmp_path / "redteam.yml").write_text(": bad: yaml: [\n", encoding="utf-8")
    errors = validate_case_references.validate_case(tmp_path)
    assert any("redteam" in e.lower() and "parse" in e.lower() for e in errors), errors


# --- missing source/evidence file produces single clear error, not per-ref noise ---

def test_missing_sources_file_gives_single_error(tmp_path):
    """When sources.yml is absent but claims reference sources, emit one error, not one per ref."""
    write_yaml(tmp_path / "claims.yml", base_claims(source_refs=["s001", "s002"]))
    errors = validate_case_references.validate_case(tmp_path)
    # Must mention the missing file
    assert any("sources.yml" in e and "missing" in e for e in errors), errors
    # Must NOT produce per-ref "not found in sources.yml" noise
    assert not any("not found in sources.yml" in e for e in errors), (
        "Got per-ref errors instead of a single missing-file error"
    )


def test_missing_evidence_file_gives_single_error(tmp_path):
    """When evidence-pack.yml is absent but claims reference evidence, emit one error."""
    write_yaml(tmp_path / "claims.yml", base_claims(evidence_refs=["e001", "e002"]))
    errors = validate_case_references.validate_case(tmp_path)
    assert any("evidence-pack.yml" in e and "missing" in e for e in errors), errors
    assert not any("not found in evidence-pack.yml" in e for e in errors), (
        "Got per-ref errors instead of a single missing-file error"
    )


# --- minimal-valid-case integration test ---

def test_minimal_valid_case_passes():
    errors = validate_case_references.validate_case(MINIMAL_CASE)
    assert errors == [], "minimal-valid-case has dangling references:\n" + "\n".join(errors)
