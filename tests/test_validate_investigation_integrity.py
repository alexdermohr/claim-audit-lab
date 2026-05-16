"""Tests for scripts/validate_investigation_integrity.py"""

import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_investigation_integrity

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "investigation-integrity.v1.schema.json"


def write_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def source(risk=0.8, adversarial=0.8, source_type="official_body"):
    return {
        "schema_version": "1.0",
        "sources": [
            {
                "schema_version": "1.0",
                "source_id": "s001",
                "label": "Official investigation",
                "url_or_ref": "https://example.org/report",
                "source_type": source_type,
                "source_weight": {
                    "institutional_interest_risk": risk,
                    "adversarial_relevance": adversarial,
                    "method_transparency": 0.9,
                },
            }
        ],
    }


def claim(status="strongly_supported", claim_kind="factual_event_claim"):
    return {
        "schema_version": "1.0",
        "claims": [
            {
                "schema_version": "1.0",
                "claim_id": "c001",
                "claim_type": "factual_event_claim",
                "claim_kind": claim_kind,
                "statement": "World claim under audit.",
                "status": status,
                "source_refs": ["s001"],
                "evidence_refs": ["e001"],
                "uncertainty": {"score": 0.2, "causes": []},
                "interpolation": {"score": 0.1, "assumptions": []},
            }
        ],
    }


def evidence_pack():
    return {
        "schema_version": "1.0",
        "evidence": [{"evidence_id": "e001", "source_ref": "s001", "claim_refs": ["c001"]}],
    }


def integrity(paths=None):
    return {
        "schema_version": "1.0",
        "case_ref": "cases/test",
        "investigations": [
            {
                "investigation_id": "inv001",
                "source_cluster_refs": ["s001"],
                "lead_institution": "Official investigation body",
                "report_role": "primary_investigation",
                "politically_sensitive": True,
                "financially_sensitive": False,
                "institutional_interest_risk": 0.8,
                "hypothesis_space_declared": ["Primary explanation"],
                "hypothesis_space_gaps": ["Alternative path not fully tested"],
                "non_tested_material_paths": paths
                if paths is not None
                else [
                    {
                        "path_id": "nt001",
                        "expected_test": "Independent replication of the material path.",
                        "justification_present": "partial",
                        "justification_quality": 0.4,
                        "materiality": 0.8,
                    }
                ],
                "adversarial_review": {"present": "partial", "notes": "External challenge was limited."},
                "integrity_verdict": "methodologically_strong_but_incompletely_adversarial",
                "downstream_constraints": ["Do not treat the report as sole closure authority."],
            }
        ],
    }


def write_case(case_dir, sources=None, claims=None, integrity_data=None):
    write_yaml(case_dir / "sources.yml", sources or source())
    write_yaml(case_dir / "claims.yml", claims or claim())
    write_yaml(case_dir / "evidence-pack.yml", evidence_pack())
    if integrity_data is not None:
        write_yaml(case_dir / "investigation-integrity.yml", integrity_data)


def validate(case_dir):
    return validate_investigation_integrity.validate_case(case_dir, load_schema())


def test_high_risk_high_adversarial_source_used_for_strong_world_claim_requires_integrity_file(tmp_path):
    write_case(tmp_path)
    errors = validate(tmp_path)
    assert any("investigation-integrity.yml must cover" in e for e in errors), errors


def test_same_source_used_only_for_reported_claim_does_not_require_full_integrity_file(tmp_path):
    write_case(tmp_path, claims=claim(claim_kind="reported_claim"))
    assert validate(tmp_path) == []


def test_low_risk_source_does_not_require_integrity_file(tmp_path):
    write_case(tmp_path, sources=source(risk=0.2, adversarial=0.8, source_type="peer_reviewed"))
    assert validate(tmp_path) == []


def test_integrity_entry_with_unresolved_non_test_path_passes_if_documented(tmp_path):
    write_case(tmp_path, integrity_data=integrity())
    assert validate(tmp_path) == []


def test_malformed_non_tested_material_paths_fails_clearly_no_traceback(tmp_path):
    data = integrity(paths=[{"path_id": "nt001"}])
    write_case(tmp_path, integrity_data=data)
    errors = validate(tmp_path)
    assert any("Schema error" in e and "expected_test" in e for e in errors), errors
    assert not any("Traceback" in e for e in errors)


def test_government_report_with_subthreshold_risk_and_high_adversarial_requires_integrity_file(tmp_path):
    sources = source(risk=0.55, adversarial=0.88, source_type="government_report")
    write_case(tmp_path, sources=sources)
    errors = validate(tmp_path)
    assert any("closure-sensitive by source_type='government_report'" in e for e in errors), errors


def test_closure_sensitive_source_type_still_exempts_reported_claim(tmp_path):
    sources = source(risk=0.55, adversarial=0.88, source_type="government_report")
    write_case(tmp_path, sources=sources, claims=claim(claim_kind="reported_claim"))
    assert validate(tmp_path) == []


def test_closure_sensitive_source_type_passes_when_integrity_file_covers_source(tmp_path):
    sources = source(risk=0.55, adversarial=0.88, source_type="government_report")
    write_case(tmp_path, sources=sources, integrity_data=integrity())
    assert validate(tmp_path) == []


def test_peer_reviewed_with_subthreshold_risk_does_not_trigger_type_based_integrity_gate(tmp_path):
    sources = source(risk=0.55, adversarial=0.88, source_type="peer_reviewed")
    write_case(tmp_path, sources=sources)
    assert validate(tmp_path) == []


def test_closure_sensitive_source_type_missing_adversarial_relevance_fails(tmp_path):
    sources = source(risk=0.55, adversarial=0.88, source_type="government_report")
    del sources["sources"][0]["source_weight"]["adversarial_relevance"]
    write_case(tmp_path, sources=sources)

    errors = validate(tmp_path)

    assert any("adversarial_relevance is missing" in e for e in errors), errors


def test_closure_sensitive_source_type_missing_source_weight_fails(tmp_path):
    sources = source(risk=0.55, adversarial=0.88, source_type="government_report")
    del sources["sources"][0]["source_weight"]
    write_case(tmp_path, sources=sources)

    errors = validate(tmp_path)

    assert any("adversarial_relevance is missing" in e for e in errors), errors


def test_claim_source_refs_string_fails_without_character_splitting(tmp_path):
    claims = claim()
    claims["claims"][0]["source_refs"] = "s001"
    write_case(tmp_path, claims=claims)

    errors = validate(tmp_path)

    assert any("claim 'c001' source_refs must be an array of strings" in e for e in errors), errors
    assert not any("source 's'" in e for e in errors), errors


def test_claim_source_refs_with_non_string_items_fails_without_traceback(tmp_path):
    claims = claim()
    claims["claims"][0]["source_refs"] = ["s001", {"bad": "ref"}, ["s002"]]
    write_case(tmp_path, claims=claims)

    errors = validate(tmp_path)

    assert any("claim 'c001' source_refs[1] must be a string" in e for e in errors), errors
    assert any("claim 'c001' source_refs[2] must be a string" in e for e in errors), errors
    assert not any("Traceback" in e for e in errors)


def test_claim_evidence_refs_string_fails(tmp_path):
    claims = claim()
    claims["claims"][0]["evidence_refs"] = "e001"
    write_case(tmp_path, claims=claims)

    errors = validate(tmp_path)

    assert any("claim 'c001' evidence_refs must be an array of strings" in e for e in errors), errors


def test_investigation_source_cluster_refs_with_non_string_items_fails(tmp_path):
    data = integrity()
    data["investigations"][0]["source_cluster_refs"] = ["s001", {"bad": "ref"}, ["s002"]]
    write_case(tmp_path, integrity_data=data)

    errors = validate(tmp_path)

    assert any("investigation 'inv001' source_cluster_refs[1] must be a string" in e for e in errors), errors
    assert any("investigation 'inv001' source_cluster_refs[2] must be a string" in e for e in errors), errors
    assert not any("Traceback" in e for e in errors)


def test_evidence_pack_evidence_scalar_fails(tmp_path):
    write_case(tmp_path)
    write_yaml(tmp_path / "evidence-pack.yml", {"schema_version": "1.0", "evidence": "not-an-array"})

    errors = validate(tmp_path)

    assert any("evidence-pack.yml 'evidence' must be an array" in e for e in errors), errors


def test_evidence_pack_evidence_non_object_item_fails_without_traceback(tmp_path):
    write_case(tmp_path)
    write_yaml(tmp_path / "evidence-pack.yml", {"schema_version": "1.0", "evidence": ["e001"]})

    errors = validate(tmp_path)

    assert any("evidence-pack.yml evidence[0] must be an object" in e for e in errors), errors
    assert not any("Traceback" in e for e in errors)


def test_evidence_pack_evidence_id_non_string_fails(tmp_path):
    write_case(tmp_path)
    write_yaml(
        tmp_path / "evidence-pack.yml",
        {"schema_version": "1.0", "evidence": [{"evidence_id": 123, "source_ref": "s001", "claim_refs": ["c001"]}]},
    )

    errors = validate(tmp_path)

    assert any("evidence-pack.yml evidence[0].evidence_id must be a string" in e for e in errors), errors


def test_evidence_pack_source_ref_non_string_fails(tmp_path):
    write_case(tmp_path)
    write_yaml(
        tmp_path / "evidence-pack.yml",
        {"schema_version": "1.0", "evidence": [{"evidence_id": "e001", "source_ref": {"bad": "ref"}, "claim_refs": ["c001"]}]},
    )

    errors = validate(tmp_path)

    assert any("evidence-pack.yml evidence[0].source_ref must be a string" in e for e in errors), errors


def test_claim_status_list_fails_without_traceback(tmp_path):
    claims = claim()
    claims["claims"][0]["status"] = ["strongly_supported"]
    write_case(tmp_path, claims=claims)

    errors = validate(tmp_path)

    assert any("claim 'c001' status must be a string" in e for e in errors), errors
    assert not any("Traceback" in e for e in errors)


def test_source_type_list_fails_without_traceback(tmp_path):
    sources = source(risk=0.55, adversarial=0.88, source_type="government_report")
    sources["sources"][0]["source_type"] = ["government_report"]
    write_case(tmp_path, sources=sources)

    errors = validate(tmp_path)

    assert any("source 's001' source_type must be a string" in e for e in errors), errors
    assert not any("Traceback" in e for e in errors)


def test_investigation_id_list_fails_without_traceback(tmp_path):
    data = integrity()
    data["investigations"][0]["investigation_id"] = ["inv001"]
    write_case(tmp_path, integrity_data=data)

    errors = validate(tmp_path)

    assert any("investigation-integrity.yml investigations[0].investigation_id must be a string" in e for e in errors), errors
    assert not any("Traceback" in e for e in errors)
