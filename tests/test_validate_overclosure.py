"""Tests for scripts/validate_overclosure.py."""

import pathlib

import validate_overclosure

FIXTURE_ROOT = pathlib.Path(__file__).parent / "fixtures" / "overclosure"


def fixture_errors(kind: str, name: str) -> list[str]:
    return validate_overclosure.validate_case(FIXTURE_ROOT / kind / name)


def test_invalid_co_causation_stronger_alternative_only_fails():
    errors = fixture_errors("invalid", "co_causation_stronger_alternative_only")
    assert any("stronger alternative" in error or "stronger primary" in error for error in errors), errors
    assert any("required_chain link" in error for error in errors), errors


def test_invalid_co_causation_missing_positive_evidence_only_fails():
    errors = fixture_errors("invalid", "co_causation_missing_positive_evidence_only")
    assert any("stronger-alternative, missing-link, non-test, non-corroboration, method-gap, or absence" in error for error in errors), errors


def test_invalid_co_causation_official_non_corroboration_only_fails():
    errors = fixture_errors("invalid", "co_causation_official_non_corroboration_only")
    assert any("non-corroboration" in error or "missing-link/alternative" in error for error in errors), errors


def test_invalid_stand3_style_overclosure_fails():
    errors = fixture_errors("invalid", "stand3_style_overclosure")
    assert any("contradicts_directly" in error for error in errors), errors
    assert any("world-causal" in error for error in errors), errors
    assert any("required_chain link" in error for error in errors), errors


def test_invalid_negated_exclusion_with_absence_language_fails():
    errors = fixture_errors("invalid", "negated_exclusion_with_absence_language")
    assert any("contradicts_directly" in error for error in errors), errors
    assert any("world-causal" in error for error in errors), errors
    assert any("required_chain link" in error for error in errors), errors


def test_invalid_causal_chain_contradicted_without_required_chain_fails():
    errors = fixture_errors("invalid", "causal_chain_contradicted_without_required_chain")
    assert any("requires non-empty required_chain" in error for error in errors), errors


def test_invalid_claim_kind_causal_chain_without_required_chain_fails():
    errors = fixture_errors("invalid", "claim_kind_causal_chain_without_required_chain")
    assert any("requires non-empty required_chain" in error for error in errors), errors


def test_invalid_world_causal_contradicted_without_direct_exclusion_fails():
    errors = fixture_errors("invalid", "world_causal_contradicted_without_direct_exclusion")
    assert any("requires a non-negated direct exclusion" in error for error in errors), errors


def test_invalid_direct_contradiction_no_evidence_found_fails():
    errors = fixture_errors("invalid", "direct_contradiction_no_evidence_found")
    assert any("contradicts_directly" in error and "absence" in error for error in errors), errors


def test_invalid_contradicted_with_unresolved_high_materiality_anomaly_fails():
    errors = fixture_errors("invalid", "contradicted_with_unresolved_high_materiality_anomaly")
    assert any("residual-path-closure" in error for error in errors), errors


def test_non_tested_path_uses_affected_claims_to_target_negative_closure(tmp_path):
    import yaml

    (tmp_path / "claims.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "claims": [
            {
                "schema_version": "1.0",
                "claim_id": "c001",
                "claim_type": "causal_claim",
                "claim_kind": "causal_claim",
                "statement": "Affected causal claim.",
                "status": "contradicted",
                "source_refs": ["s001"],
                "direct_incompatibility_basis": "Temporal exclusion rules out the required link.",
                "uncertainty": {"score": 0.2, "causes": []},
                "interpolation": {"score": 0.1, "assumptions": []},
            },
            {
                "schema_version": "1.0",
                "claim_id": "c002",
                "claim_type": "causal_claim",
                "claim_kind": "causal_claim",
                "statement": "Unaffected causal claim.",
                "status": "contradicted",
                "source_refs": ["s001"],
                "direct_incompatibility_basis": "Temporal exclusion rules out the required link.",
                "uncertainty": {"score": 0.2, "causes": []},
                "interpolation": {"score": 0.1, "assumptions": []},
            },
        ],
    }), encoding="utf-8")
    (tmp_path / "investigation-integrity.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "case_ref": "cases/test",
        "investigations": [{
            "investigation_id": "inv001",
            "source_cluster_refs": ["s001"],
            "lead_institution": "Test institution",
            "report_role": "primary_investigation",
            "politically_sensitive": False,
            "financially_sensitive": False,
            "institutional_interest_risk": 0.0,
            "hypothesis_space_declared": ["main"],
            "hypothesis_space_gaps": ["gap"],
            "non_tested_material_paths": [{
                "path_id": "nt001",
                "expected_test": "Test affected path.",
                "justification_present": "partial",
                "justification_quality": 0.4,
                "materiality": 0.8,
                "affected_claims": ["c001"],
            }],
            "adversarial_review": {"present": "unknown", "notes": "Unknown."},
            "integrity_verdict": "insufficient_information",
            "downstream_constraints": ["No overclosure."],
        }],
    }), encoding="utf-8")

    errors = validate_overclosure.validate_case(tmp_path)

    assert any("claim 'c001'" in error and "nt001" in error for error in errors), errors
    assert not any("claim 'c002'" in error and "nt001" in error for error in errors), errors


def test_non_tested_path_closed_residual_path_allows_negative_closure(tmp_path):
    import yaml

    (tmp_path / "claims.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "claims": [{
            "schema_version": "1.0",
            "claim_id": "c001",
            "claim_type": "causal_claim",
            "claim_kind": "causal_claim",
            "statement": "Affected causal claim.",
            "status": "contradicted",
            "source_refs": ["s001"],
            "direct_incompatibility_basis": "Temporal exclusion rules out the required link.",
            "uncertainty": {"score": 0.2, "causes": []},
            "interpolation": {"score": 0.1, "assumptions": []},
        }],
    }), encoding="utf-8")
    (tmp_path / "investigation-integrity.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "case_ref": "cases/test",
        "investigations": [{
            "investigation_id": "inv001",
            "source_cluster_refs": ["s001"],
            "lead_institution": "Test institution",
            "report_role": "primary_investigation",
            "politically_sensitive": False,
            "financially_sensitive": False,
            "institutional_interest_risk": 0.0,
            "hypothesis_space_declared": ["main"],
            "hypothesis_space_gaps": ["gap"],
            "non_tested_material_paths": [{
                "path_id": "nt001",
                "expected_test": "Test affected path.",
                "justification_present": "partial",
                "justification_quality": 0.4,
                "materiality": 0.8,
                "affected_claims": ["c001"],
                "residual_path_closure": {
                    "status": "closed",
                    "rationale": "Direct temporal exclusion closes this path.",
                    "evidence_refs": ["e001"],
                },
            }],
            "adversarial_review": {"present": "unknown", "notes": "Unknown."},
            "integrity_verdict": "insufficient_information",
            "downstream_constraints": ["No overclosure."],
        }],
    }), encoding="utf-8")

    (tmp_path / "evidence-pack.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "evidence": [{"evidence_id": "e001", "source_ref": "s001", "claim_refs": ["c001"]}],
    }), encoding="utf-8")

    assert validate_overclosure.validate_case(tmp_path) == []


def test_non_tested_path_unknown_affected_claim_fails(tmp_path):
    import yaml

    (tmp_path / "claims.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "claims": [{
            "schema_version": "1.0",
            "claim_id": "c001",
            "claim_type": "causal_claim",
            "claim_kind": "causal_claim",
            "statement": "Affected causal claim.",
            "status": "contradicted",
            "source_refs": ["s001"],
            "direct_incompatibility_basis": "Temporal exclusion rules out the required link.",
            "uncertainty": {"score": 0.2, "causes": []},
            "interpolation": {"score": 0.1, "assumptions": []},
        }],
    }), encoding="utf-8")
    (tmp_path / "investigation-integrity.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "case_ref": "cases/test",
        "investigations": [{
            "investigation_id": "inv001",
            "source_cluster_refs": ["s001"],
            "lead_institution": "Test institution",
            "report_role": "primary_investigation",
            "politically_sensitive": False,
            "financially_sensitive": False,
            "institutional_interest_risk": 0.0,
            "hypothesis_space_declared": ["main"],
            "hypothesis_space_gaps": ["gap"],
            "non_tested_material_paths": [{
                "path_id": "nt001",
                "expected_test": "Test affected path.",
                "justification_present": "partial",
                "justification_quality": 0.4,
                "materiality": 0.8,
                "affected_claims": ["c001-typo"],
            }],
            "adversarial_review": {"present": "unknown", "notes": "Unknown."},
            "integrity_verdict": "insufficient_information",
            "downstream_constraints": ["No overclosure."],
        }],
    }), encoding="utf-8")

    errors = validate_overclosure.validate_case(tmp_path)

    assert any("unknown affected_claim 'c001-typo'" in error for error in errors), errors


def test_non_tested_path_closed_unknown_affected_claim_still_fails(tmp_path):
    import yaml

    (tmp_path / "claims.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "claims": [{
            "schema_version": "1.0",
            "claim_id": "c001",
            "claim_type": "causal_claim",
            "claim_kind": "causal_claim",
            "statement": "Affected causal claim.",
            "status": "contradicted",
            "source_refs": ["s001"],
            "direct_incompatibility_basis": "Temporal exclusion rules out the required link.",
            "uncertainty": {"score": 0.2, "causes": []},
            "interpolation": {"score": 0.1, "assumptions": []},
        }],
    }), encoding="utf-8")
    (tmp_path / "evidence-pack.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "evidence": [{"evidence_id": "e001", "source_ref": "s001", "claim_refs": ["c001"]}],
    }), encoding="utf-8")
    (tmp_path / "investigation-integrity.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "case_ref": "cases/test",
        "investigations": [{
            "investigation_id": "inv001",
            "source_cluster_refs": ["s001"],
            "lead_institution": "Test institution",
            "report_role": "primary_investigation",
            "politically_sensitive": False,
            "financially_sensitive": False,
            "institutional_interest_risk": 0.0,
            "hypothesis_space_declared": ["main"],
            "hypothesis_space_gaps": ["gap"],
            "non_tested_material_paths": [{
                "path_id": "nt001",
                "expected_test": "Test affected path.",
                "justification_present": "partial",
                "justification_quality": 0.4,
                "materiality": 0.8,
                "affected_claims": ["c001-typo"],
                "residual_path_closure": {
                    "status": "closed",
                    "rationale": "Direct temporal exclusion closes this path.",
                    "evidence_refs": ["e001"],
                },
            }],
            "adversarial_review": {"present": "unknown", "notes": "Unknown."},
            "integrity_verdict": "insufficient_information",
            "downstream_constraints": ["No overclosure."],
        }],
    }), encoding="utf-8")

    errors = validate_overclosure.validate_case(tmp_path)

    assert any("unknown affected_claim 'c001-typo'" in error for error in errors), errors


def test_closed_residual_path_unknown_evidence_ref_fails(tmp_path):
    import yaml

    (tmp_path / "claims.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "claims": [{
            "schema_version": "1.0",
            "claim_id": "c001",
            "claim_type": "causal_claim",
            "claim_kind": "causal_claim",
            "statement": "Affected causal claim.",
            "status": "contradicted",
            "source_refs": ["s001"],
            "direct_incompatibility_basis": "Temporal exclusion rules out the required link.",
            "uncertainty": {"score": 0.2, "causes": []},
            "interpolation": {"score": 0.1, "assumptions": []},
        }],
    }), encoding="utf-8")
    (tmp_path / "evidence-pack.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "evidence": [{"evidence_id": "e001", "source_ref": "s001", "claim_refs": ["c001"]}],
    }), encoding="utf-8")
    (tmp_path / "investigation-integrity.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "case_ref": "cases/test",
        "investigations": [{
            "investigation_id": "inv001",
            "source_cluster_refs": ["s001"],
            "lead_institution": "Test institution",
            "report_role": "primary_investigation",
            "politically_sensitive": False,
            "financially_sensitive": False,
            "institutional_interest_risk": 0.0,
            "hypothesis_space_declared": ["main"],
            "hypothesis_space_gaps": ["gap"],
            "non_tested_material_paths": [{
                "path_id": "nt001",
                "expected_test": "Test affected path.",
                "justification_present": "partial",
                "justification_quality": 0.4,
                "materiality": 0.8,
                "affected_claims": ["c001"],
                "residual_path_closure": {
                    "status": "closed",
                    "rationale": "Direct temporal exclusion closes this path.",
                    "evidence_refs": ["e999"],
                },
            }],
            "adversarial_review": {"present": "unknown", "notes": "Unknown."},
            "integrity_verdict": "insufficient_information",
            "downstream_constraints": ["No overclosure."],
        }],
    }), encoding="utf-8")

    errors = validate_overclosure.validate_case(tmp_path)

    assert any("unknown evidence_ref 'e999'" in error for error in errors), errors


def test_non_tested_path_closed_without_evidence_refs_still_blocks(tmp_path):
    import yaml

    (tmp_path / "claims.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "claims": [{
            "schema_version": "1.0",
            "claim_id": "c001",
            "claim_type": "causal_claim",
            "claim_kind": "causal_claim",
            "statement": "Affected causal claim.",
            "status": "contradicted",
            "source_refs": ["s001"],
            "direct_incompatibility_basis": "Temporal exclusion rules out the required link.",
            "uncertainty": {"score": 0.2, "causes": []},
            "interpolation": {"score": 0.1, "assumptions": []},
        }],
    }), encoding="utf-8")
    (tmp_path / "investigation-integrity.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "case_ref": "cases/test",
        "investigations": [{
            "investigation_id": "inv001",
            "source_cluster_refs": ["s001"],
            "lead_institution": "Test institution",
            "report_role": "primary_investigation",
            "politically_sensitive": False,
            "financially_sensitive": False,
            "institutional_interest_risk": 0.0,
            "hypothesis_space_declared": ["main"],
            "hypothesis_space_gaps": ["gap"],
            "non_tested_material_paths": [{
                "path_id": "nt001",
                "expected_test": "Test affected path.",
                "justification_present": "partial",
                "justification_quality": 0.4,
                "materiality": 0.8,
                "affected_claims": ["c001"],
                "residual_path_closure": {"status": "closed", "rationale": "Direct temporal exclusion closes this path."},
            }],
            "adversarial_review": {"present": "unknown", "notes": "Unknown."},
            "integrity_verdict": "insufficient_information",
            "downstream_constraints": ["No overclosure."],
        }],
    }), encoding="utf-8")

    errors = validate_overclosure.validate_case(tmp_path)

    assert any("claim 'c001'" in error and "nt001" in error for error in errors), errors


def test_non_tested_path_closed_without_rationale_still_blocks(tmp_path):
    import yaml

    (tmp_path / "claims.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "claims": [{
            "schema_version": "1.0",
            "claim_id": "c001",
            "claim_type": "causal_claim",
            "claim_kind": "causal_claim",
            "statement": "Affected causal claim.",
            "status": "contradicted",
            "source_refs": ["s001"],
            "direct_incompatibility_basis": "Temporal exclusion rules out the required link.",
            "uncertainty": {"score": 0.2, "causes": []},
            "interpolation": {"score": 0.1, "assumptions": []},
        }],
    }), encoding="utf-8")
    (tmp_path / "investigation-integrity.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "case_ref": "cases/test",
        "investigations": [{
            "investigation_id": "inv001",
            "source_cluster_refs": ["s001"],
            "lead_institution": "Test institution",
            "report_role": "primary_investigation",
            "politically_sensitive": False,
            "financially_sensitive": False,
            "institutional_interest_risk": 0.0,
            "hypothesis_space_declared": ["main"],
            "hypothesis_space_gaps": ["gap"],
            "non_tested_material_paths": [{
                "path_id": "nt001",
                "expected_test": "Test affected path.",
                "justification_present": "partial",
                "justification_quality": 0.4,
                "materiality": 0.8,
                "affected_claims": ["c001"],
                "residual_path_closure": {"status": "closed", "rationale": " ", "evidence_refs": ["e001"]},
            }],
            "adversarial_review": {"present": "unknown", "notes": "Unknown."},
            "integrity_verdict": "insufficient_information",
            "downstream_constraints": ["No overclosure."],
        }],
    }), encoding="utf-8")

    errors = validate_overclosure.validate_case(tmp_path)

    assert any("claim 'c001'" in error and "nt001" in error for error in errors), errors


def test_non_tested_path_open_residual_path_blocks_negative_closure(tmp_path):
    import yaml

    (tmp_path / "claims.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "claims": [{
            "schema_version": "1.0",
            "claim_id": "c001",
            "claim_type": "causal_claim",
            "claim_kind": "causal_claim",
            "statement": "Affected causal claim.",
            "status": "contradicted",
            "source_refs": ["s001"],
            "direct_incompatibility_basis": "Temporal exclusion rules out the required link.",
            "uncertainty": {"score": 0.2, "causes": []},
            "interpolation": {"score": 0.1, "assumptions": []},
        }],
    }), encoding="utf-8")
    (tmp_path / "investigation-integrity.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "case_ref": "cases/test",
        "investigations": [{
            "investigation_id": "inv001",
            "source_cluster_refs": ["s001"],
            "lead_institution": "Test institution",
            "report_role": "primary_investigation",
            "politically_sensitive": False,
            "financially_sensitive": False,
            "institutional_interest_risk": 0.0,
            "hypothesis_space_declared": ["main"],
            "hypothesis_space_gaps": ["gap"],
            "non_tested_material_paths": [{
                "path_id": "nt001",
                "expected_test": "Test affected path.",
                "justification_present": "partial",
                "justification_quality": 0.4,
                "materiality": 0.8,
                "affected_claims": ["c001"],
                "residual_path_closure": {"status": "open", "rationale": "Still unclosed.", "evidence_refs": ["e001"]},
            }],
            "adversarial_review": {"present": "unknown", "notes": "Unknown."},
            "integrity_verdict": "insufficient_information",
            "downstream_constraints": ["No overclosure."],
        }],
    }), encoding="utf-8")

    errors = validate_overclosure.validate_case(tmp_path)

    assert any("claim 'c001'" in error and "nt001" in error for error in errors), errors


def test_non_tested_path_low_materiality_still_validates_references(tmp_path):
    import yaml

    (tmp_path / "claims.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "claims": [{
            "schema_version": "1.0",
            "claim_id": "c001",
            "claim_type": "causal_claim",
            "claim_kind": "causal_claim",
            "statement": "Affected causal claim.",
            "status": "contradicted",
            "source_refs": ["s001"],
            "direct_incompatibility_basis": "Temporal exclusion rules out the required link.",
            "uncertainty": {"score": 0.2, "causes": []},
            "interpolation": {"score": 0.1, "assumptions": []},
        }],
    }), encoding="utf-8")
    (tmp_path / "evidence-pack.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "evidence": [{"evidence_id": "e001", "source_ref": "s001", "claim_refs": ["c001"]}],
    }), encoding="utf-8")
    (tmp_path / "investigation-integrity.yml").write_text(yaml.safe_dump({
        "schema_version": "1.0",
        "case_ref": "cases/test",
        "investigations": [{
            "investigation_id": "inv001",
            "source_cluster_refs": ["s001"],
            "lead_institution": "Test institution",
            "report_role": "primary_investigation",
            "politically_sensitive": False,
            "financially_sensitive": False,
            "institutional_interest_risk": 0.0,
            "hypothesis_space_declared": ["main"],
            "hypothesis_space_gaps": ["gap"],
            "non_tested_material_paths": [{
                "path_id": "nt-low",
                "expected_test": "Low-materiality path still needs valid references.",
                "justification_present": "yes",
                "justification_quality": 1.0,
                "materiality": 0.1,
                "affected_claims": ["c999"],
                "residual_path_closure": {
                    "status": "open",
                    "rationale": "Reference-integrity check only.",
                    "evidence_refs": ["e999"],
                },
            }],
            "adversarial_review": {"present": "unknown", "notes": "Unknown."},
            "integrity_verdict": "insufficient_information",
            "downstream_constraints": ["No overclosure."],
        }],
    }), encoding="utf-8")

    errors = validate_overclosure.validate_case(tmp_path)

    assert any("unknown affected_claim 'c999'" in error for error in errors), errors
    assert any("unknown evidence_ref 'e999'" in error for error in errors), errors
    assert not any("claim 'c001'" in error and "nt-low" in error for error in errors), errors


def test_valid_causal_temporal_exclusion_contradiction_passes():
    assert fixture_errors("valid", "causal_temporal_exclusion_contradiction") == []


def test_valid_co_causation_downgraded_to_weak_passes():
    assert fixture_errors("valid", "co_causation_downgraded_to_weak") == []


def test_valid_reported_source_report_established_passes():
    assert fixture_errors("valid", "reported_source_report_established") == []


def test_cli_reports_invalid_fixture(capsys):
    exit_code = validate_overclosure.main(str(FIXTURE_ROOT / "invalid" / "co_causation_stronger_alternative_only"))
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL" in captured.out
