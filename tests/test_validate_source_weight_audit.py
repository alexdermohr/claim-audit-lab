"""Tests for scripts/validate_source_weight_audit.py"""

import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_source_weight_audit

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "source-weight-audit.v1.schema.json"
MINIMAL_CASE = pathlib.Path(__file__).parent.parent / "cases" / "sandbox" / "minimal-valid-case"


def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def write_yaml(path: pathlib.Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False)


def base_sources(source_id="s001", with_weight=True) -> dict:
    source = {
        "schema_version": "1.0",
        "source_id": source_id,
        "label": "Test source",
        "url_or_ref": "https://example.org/source",
        "source_type": "official_body",
    }
    if with_weight:
        source["source_weight"] = {"primary_proximity": 0.5}
    return {"schema_version": "1.0", "sources": [source]}


def base_evidence_pack(evidence_id="e001", source_ref="s001") -> dict:
    return {
        "schema_version": "1.0",
        "evidence": [
            {
                "evidence_id": evidence_id,
                "source_ref": source_ref,
                "claim_refs": ["c001"],
                "type": "official_statement",
                "summary": "Test summary.",
                "verbatim_or_ref": "See source.",
                "supports": ["c001"],
                "contradicts": [],
            }
        ],
    }


def base_audit(source_ref="s001", evidence_refs=None) -> dict:
    return {
        "schema_version": "1.0",
        "case_ref": "cases/test",
        "audited_at": "2026-05-14",
        "auditor": "qa",
        "records": [
            {
                "source_ref": source_ref,
                "questions": ["Why was this source weighted this way?"],
                "evidence_refs": evidence_refs if evidence_refs is not None else ["e001"],
                "disputed": False,
                "notes": "Test audit notes.",
            }
        ],
    }


def test_weighted_source_without_audit_fails(tmp_path):
    write_yaml(tmp_path / "sources.yml", base_sources())
    errors = validate_source_weight_audit.validate_case(tmp_path, load_schema())
    assert any("source-weight-audit.yml required" in e for e in errors), errors


def test_weighted_source_with_audit_passes(tmp_path):
    write_yaml(tmp_path / "sources.yml", base_sources())
    write_yaml(tmp_path / "evidence-pack.yml", base_evidence_pack())
    write_yaml(tmp_path / "source-weight-audit.yml", base_audit())
    errors = validate_source_weight_audit.validate_case(tmp_path, load_schema())
    assert errors == []


def test_unweighted_source_without_audit_passes(tmp_path):
    write_yaml(tmp_path / "sources.yml", base_sources(with_weight=False))
    errors = validate_source_weight_audit.validate_case(tmp_path, load_schema())
    assert errors == []


def test_missing_weighted_source_record_fails(tmp_path):
    payload = base_sources("s001")
    payload["sources"].append(base_sources("s002")["sources"][0])
    write_yaml(tmp_path / "sources.yml", payload)
    write_yaml(tmp_path / "evidence-pack.yml", base_evidence_pack())
    write_yaml(tmp_path / "source-weight-audit.yml", base_audit("s001"))
    errors = validate_source_weight_audit.validate_case(tmp_path, load_schema())
    assert any("s002" in e and "requires" in e for e in errors), errors


def test_audit_unknown_source_ref_fails(tmp_path):
    write_yaml(tmp_path / "sources.yml", base_sources("s001"))
    write_yaml(tmp_path / "source-weight-audit.yml", base_audit("s999", evidence_refs=[]))
    errors = validate_source_weight_audit.validate_case(tmp_path, load_schema())
    assert any("s999" in e and "not found" in e for e in errors), errors


def test_audit_unknown_evidence_ref_fails(tmp_path):
    write_yaml(tmp_path / "sources.yml", base_sources())
    write_yaml(tmp_path / "evidence-pack.yml", base_evidence_pack("e001"))
    write_yaml(tmp_path / "source-weight-audit.yml", base_audit(evidence_refs=["e999"]))
    errors = validate_source_weight_audit.validate_case(tmp_path, load_schema())
    assert any("e999" in e and "not found" in e for e in errors), errors



def test_audit_requires_same_source_evidence_ref(tmp_path):
    write_yaml(tmp_path / "sources.yml", base_sources("s001"))
    write_yaml(tmp_path / "evidence-pack.yml", base_evidence_pack("e001", source_ref="s999"))
    write_yaml(tmp_path / "source-weight-audit.yml", base_audit("s001", evidence_refs=["e001"]))
    errors = validate_source_weight_audit.validate_case(tmp_path, load_schema())
    assert any("same source" in e for e in errors), errors


def test_main_accepts_single_case_path(tmp_path):
    write_yaml(tmp_path / "sources.yml", base_sources())
    write_yaml(tmp_path / "evidence-pack.yml", base_evidence_pack())
    write_yaml(tmp_path / "source-weight-audit.yml", base_audit())
    assert validate_source_weight_audit.main(str(tmp_path)) == 0


def test_minimal_valid_case_source_weight_audit_passes():
    errors = validate_source_weight_audit.validate_case(MINIMAL_CASE, load_schema())
    assert errors == [], "minimal-valid-case has source-weight audit errors:\n" + "\n".join(errors)
