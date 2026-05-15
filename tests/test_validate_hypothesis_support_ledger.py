"""Tests for scripts/validate_hypothesis_support_ledger.py"""

import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_hypothesis_support_ledger

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "hypothesis-support-ledger.v1.schema.json"


def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def write_yaml(path: pathlib.Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False)


def base_hypotheses(status="plausible") -> dict:
    return {
        "schema_version": "1.0",
        "hypotheses": [
            {
                "id": "h1",
                "label": "fixture_hypothesis",
                "description": "Fixture hypothesis.",
                "status": status,
                "supporting_evidence": ["e001"],
                "weaknesses": ["Fixture weakness."],
            }
        ],
    }


def base_sources(source_id="s001") -> dict:
    return {
        "schema_version": "1.0",
        "sources": [
            {
                "schema_version": "1.0",
                "source_id": source_id,
                "label": "Fixture source",
                "url_or_ref": "https://example.org/source",
                "source_type": "official_body",
            }
        ],
    }


def base_evidence_pack(evidence_id="e001", source_ref="s001") -> dict:
    return {
        "schema_version": "1.0",
        "evidence": [
            {
                "evidence_id": evidence_id,
                "source_ref": source_ref,
                "claim_refs": ["c001"],
                "type": "official_statement",
                "summary": "Fixture evidence summary.",
                "verbatim_or_ref": "Fixture source reference.",
                "supports": ["c001"],
                "contradicts": [],
            }
        ],
    }


def base_ledger(hypothesis_ref="h1", evidence_refs=None, source_refs=None, **overrides) -> dict:
    record = {
        "hypothesis_ref": hypothesis_ref,
        "support_search_status": "completed",
        "strongest_supporting_argument": "Fixture support statement.",
        "supporting_evidence_refs": ["e001"] if evidence_refs is None else evidence_refs,
        "best_supporting_source_refs": ["s001"] if source_refs is None else source_refs,
        "steelman": "Fixture steelman.",
        "missing_for_upgrade": ["Fixture upgrade requirement."],
        "searched_for": ["Fixture support search."],
        "not_found": [],
        "notes": "Fixture notes.",
        "support_quality_score": 0.5,
    }
    record.update(overrides)
    return {
        "schema_version": "1.0",
        "case_ref": "cases/test",
        "audited_at": "2026-05-14",
        "auditor": "qa",
        "records": [record],
    }


def write_valid_support_case(tmp_path, hypotheses_status="plausible", ledger=None):
    write_yaml(tmp_path / "hypotheses.yml", base_hypotheses(hypotheses_status))
    write_yaml(tmp_path / "sources.yml", base_sources())
    write_yaml(tmp_path / "evidence-pack.yml", base_evidence_pack())
    write_yaml(tmp_path / "hypothesis-support-ledger.yml", ledger or base_ledger())


def test_missing_ledger_with_hypotheses_fails(tmp_path):
    write_yaml(tmp_path / "hypotheses.yml", base_hypotheses())
    errors = validate_hypothesis_support_ledger.validate_case(tmp_path, load_schema())
    assert any("hypothesis-support-ledger.yml required" in e for e in errors), errors


def test_missing_record_for_hypothesis_fails(tmp_path):
    hypotheses = base_hypotheses()
    hypotheses["hypotheses"].append(
        {
            "id": "h2",
            "label": "fixture_hypothesis_two",
            "description": "Fixture hypothesis two.",
            "status": "plausible",
            "supporting_evidence": [],
            "weaknesses": [],
        }
    )
    write_yaml(tmp_path / "hypotheses.yml", hypotheses)
    write_yaml(tmp_path / "sources.yml", base_sources())
    write_yaml(tmp_path / "evidence-pack.yml", base_evidence_pack())
    write_yaml(tmp_path / "hypothesis-support-ledger.yml", base_ledger())
    errors = validate_hypothesis_support_ledger.validate_case(tmp_path, load_schema())
    assert any("h2" in e and "requires" in e for e in errors), errors



def test_duplicate_hypothesis_id_fails(tmp_path):
    hypotheses = base_hypotheses()
    hypotheses["hypotheses"].append(dict(hypotheses["hypotheses"][0]))
    write_yaml(tmp_path / "hypotheses.yml", hypotheses)
    write_yaml(tmp_path / "sources.yml", base_sources())
    write_yaml(tmp_path / "evidence-pack.yml", base_evidence_pack())
    write_yaml(tmp_path / "hypothesis-support-ledger.yml", base_ledger())
    errors = validate_hypothesis_support_ledger.validate_case(tmp_path, load_schema())
    assert any("duplicate hypothesis id" in e and "h1" in e for e in errors), errors


def test_hypothesis_missing_id_fails(tmp_path):
    hypotheses = base_hypotheses()
    del hypotheses["hypotheses"][0]["id"]
    write_yaml(tmp_path / "hypotheses.yml", hypotheses)
    write_yaml(tmp_path / "sources.yml", base_sources())
    write_yaml(tmp_path / "evidence-pack.yml", base_evidence_pack())
    write_yaml(tmp_path / "hypothesis-support-ledger.yml", base_ledger())
    errors = validate_hypothesis_support_ledger.validate_case(tmp_path, load_schema())
    assert any("missing required id" in e for e in errors), errors

def test_unknown_hypothesis_ref_fails(tmp_path):
    write_valid_support_case(tmp_path, ledger=base_ledger("h999"))
    errors = validate_hypothesis_support_ledger.validate_case(tmp_path, load_schema())
    assert any("h999" in e and "not found" in e for e in errors), errors


def test_duplicate_hypothesis_ref_fails(tmp_path):
    ledger = base_ledger()
    ledger["records"].append(dict(ledger["records"][0]))
    write_valid_support_case(tmp_path, ledger=ledger)
    errors = validate_hypothesis_support_ledger.validate_case(tmp_path, load_schema())
    assert any("duplicate" in e and "h1" in e for e in errors), errors


def test_malformed_evidence_pack_reports_parse_without_ref_cascade(tmp_path):
    write_valid_support_case(tmp_path)
    (tmp_path / "evidence-pack.yml").write_text("evidence: [unterminated", encoding="utf-8")
    errors = validate_hypothesis_support_ledger.validate_case(tmp_path, load_schema())
    assert any("Could not parse evidence-pack.yml" in e for e in errors), errors
    assert not any("evidence_ref 'e001' not found" in e for e in errors), errors


def test_unknown_evidence_ref_fails(tmp_path):
    write_valid_support_case(tmp_path, ledger=base_ledger(evidence_refs=["e999"]))
    errors = validate_hypothesis_support_ledger.validate_case(tmp_path, load_schema())
    assert any("e999" in e and "not found" in e for e in errors), errors


def test_unknown_source_ref_fails(tmp_path):
    write_valid_support_case(tmp_path, ledger=base_ledger(source_refs=["s999"]))
    errors = validate_hypothesis_support_ledger.validate_case(tmp_path, load_schema())
    assert any("s999" in e and "not found" in e for e in errors), errors


def test_weak_hypothesis_without_steelman_fails(tmp_path):
    write_valid_support_case(tmp_path, hypotheses_status="weak", ledger=base_ledger(steelman=""))
    errors = validate_hypothesis_support_ledger.validate_case(tmp_path, load_schema())
    assert any("steelman" in e for e in errors), errors


def test_contradicted_hypothesis_without_missing_for_upgrade_fails(tmp_path):
    write_valid_support_case(
        tmp_path,
        hypotheses_status="contradicted",
        ledger=base_ledger(missing_for_upgrade=[]),
    )
    errors = validate_hypothesis_support_ledger.validate_case(tmp_path, load_schema())
    assert any("missing_for_upgrade" in e for e in errors), errors


def test_empty_supporting_evidence_without_not_found_fails(tmp_path):
    write_valid_support_case(tmp_path, ledger=base_ledger(evidence_refs=[], not_found=[]))
    errors = validate_hypothesis_support_ledger.validate_case(tmp_path, load_schema())
    assert any("not_found" in e for e in errors), errors



def test_blocked_downgraded_hypothesis_without_not_found_fails(tmp_path):
    write_valid_support_case(
        tmp_path,
        hypotheses_status="weak",
        ledger=base_ledger(
            support_search_status="blocked",
            supporting_evidence_refs=["e001"],
            not_found=[],
        ),
    )
    errors = validate_hypothesis_support_ledger.validate_case(tmp_path, load_schema())
    assert any("blocked" in e and "not_found" in e for e in errors), errors


def test_completed_downgraded_with_missing_for_upgrade_without_not_found_fails(tmp_path):
    write_valid_support_case(
        tmp_path,
        hypotheses_status="contradicted",
        ledger=base_ledger(supporting_evidence_refs=["e001"], not_found=[]),
    )
    errors = validate_hypothesis_support_ledger.validate_case(tmp_path, load_schema())
    assert any("missing_for_upgrade" in e and "not_found" in e for e in errors), errors


def test_synthetic_minimal_hypothesis_support_ledger_passes(tmp_path):
    write_valid_support_case(tmp_path)
    errors = validate_hypothesis_support_ledger.validate_case(tmp_path, load_schema())
    assert errors == [], "synthetic minimal case has hypothesis-support ledger errors:\n" + "\n".join(errors)
