#!/usr/bin/env python3
"""Tests for validate_bias_response.py."""

from pathlib import Path

import pytest
import yaml

import generate_bias_signals as gbs
import validate_bias_response as vbr

SCHEMA = vbr.load_schema(vbr.RESPONSE_SCHEMA_PATH)


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def base_claim(claim_id, status="plausible", **extra):
    base = {
        "claim_id": claim_id,
        "claim_type": extra.pop("claim_type", "factual_event_claim"),
        "statement": extra.pop("statement", f"Statement {claim_id}"),
        "status": status,
    }
    base.update(extra)
    return base


def severe_case(tmp_path, lifecycle_status):
    """A case that generates exactly one severe (0.82) assessment_verdict_mismatch signal."""
    case = tmp_path / "cases" / "severe"
    case.mkdir(parents=True)
    write(case / "claims.yml", {"claims": [base_claim("c001", status="weak")]})
    write(case / "assessment.md", "The audit clearly proves c001 beyond all doubt.")
    write(case / "lifecycle.yml", {"status": lifecycle_status})
    signals = gbs.generate_for_case(case)
    assert len(signals) == 1 and signals[0]["severity"] >= 0.75
    return case, signals[0]["signal_id"]


def soft_case(tmp_path, lifecycle_status):
    """A case that generates exactly one non-severe (0.60) comparative_claim_underframed signal."""
    case = tmp_path / "cases" / "soft"
    case.mkdir(parents=True)
    write(case / "claims.yml", {"claims": [
        base_claim("c001", claim_kind="comparative_claim", requires=["timeline"])
    ]})
    write(case / "lifecycle.yml", {"status": lifecycle_status})
    signals = gbs.generate_for_case(case)
    assert len(signals) == 1 and signals[0]["severity"] < 0.75
    return case, signals[0]["signal_id"]


def errors_of(case):
    return vbr.validate_case(case, SCHEMA).errors


class TestDraftMode:
    def test_draft_without_response_passes(self, tmp_path):
        case, _ = severe_case(tmp_path, "draft")
        result = vbr.validate_case(case, SCHEMA)
        assert result.errors == []
        assert result.warnings  # open signals reported, not failing

    def test_draft_unknown_signal_ref_is_warning_not_error(self, tmp_path):
        case, _ = severe_case(tmp_path, "draft")
        write(case / "bias-response.yml", {
            "schema_version": "1.0",
            "case_ref": "cases/severe",
            "responses": [{
                "signal_ref": "bs_000000000000",
                "response_status": "false_positive",
                "rationale": "does not apply",
                "mitigation_refs": ["claims.yml"],
            }],
        })
        result = vbr.validate_case(case, SCHEMA)
        assert result.errors == []
        assert any("not generated" in w for w in result.warnings)

    def test_malformed_response_fails_even_in_draft(self, tmp_path):
        case, signal_id = severe_case(tmp_path, "draft")
        write(case / "bias-response.yml", {
            "schema_version": "1.0",
            "case_ref": "cases/severe",
            "responses": [{
                "signal_ref": signal_id,
                "response_status": "acknowledged",  # not permitted
                "rationale": "seen it",
            }],
        })
        assert errors_of(case)

    def test_acknowledged_status_is_rejected(self, tmp_path):
        case, signal_id = severe_case(tmp_path, "draft")
        write(case / "bias-response.yml", {
            "schema_version": "1.0",
            "case_ref": "cases/severe",
            "responses": [{
                "signal_ref": signal_id,
                "response_status": "noted",
                "rationale": "noted",
            }],
        })
        errs = errors_of(case)
        assert any("Schema error" in e for e in errs)


class TestFinalMode:
    def test_final_without_response_fails(self, tmp_path):
        case, _ = severe_case(tmp_path, "final_under_uncertainty")
        errs = errors_of(case)
        assert any("has no response" in e for e in errs)

    def test_final_mitigated_without_refs_fails(self, tmp_path):
        case, signal_id = severe_case(tmp_path, "final_under_uncertainty")
        write(case / "bias-response.yml", {
            "schema_version": "1.0",
            "case_ref": "cases/severe",
            "responses": [{
                "signal_ref": signal_id,
                "response_status": "mitigated",
                "rationale": "softened the language",
                "mitigation_refs": [],
            }],
        })
        errs = errors_of(case)
        assert any("mitigation_refs" in e for e in errs)

    def test_final_mitigated_with_existing_ref_passes(self, tmp_path):
        case, signal_id = severe_case(tmp_path, "final_under_uncertainty")
        write(case / "bias-response.yml", {
            "schema_version": "1.0",
            "case_ref": "cases/severe",
            "responses": [{
                "signal_ref": signal_id,
                "response_status": "mitigated",
                "rationale": "aligned assessment language to the weak status",
                "mitigation_refs": ["assessment.md", "claims.yml"],
            }],
        })
        assert errors_of(case) == []

    def test_final_mitigated_with_escaping_ref_fails(self, tmp_path):
        case, signal_id = severe_case(tmp_path, "final_under_uncertainty")
        (tmp_path / "cases" / "outside.yml").write_text("x: 1", encoding="utf-8")
        write(case / "bias-response.yml", {
            "schema_version": "1.0",
            "case_ref": "cases/severe",
            "responses": [{
                "signal_ref": signal_id,
                "response_status": "mitigated",
                "rationale": "cites a sibling file outside the case",
                "mitigation_refs": ["../outside.yml"],
            }],
        })
        assert errors_of(case)

    def test_final_mitigated_with_absolute_ref_fails(self, tmp_path):
        case, signal_id = severe_case(tmp_path, "final_under_uncertainty")
        write(case / "bias-response.yml", {
            "schema_version": "1.0",
            "case_ref": "cases/severe",
            "responses": [{
                "signal_ref": signal_id,
                "response_status": "mitigated",
                "rationale": "cites an absolute system path",
                "mitigation_refs": ["/etc/hosts"],
            }],
        })
        assert errors_of(case)

    def test_final_mitigated_with_anchor_ref_passes(self, tmp_path):
        case, signal_id = severe_case(tmp_path, "final_under_uncertainty")
        write(case / "bias-response.yml", {
            "schema_version": "1.0",
            "case_ref": "cases/severe",
            "responses": [{
                "signal_ref": signal_id,
                "response_status": "mitigated",
                "rationale": "anchored ref to an existing in-case artifact",
                "mitigation_refs": ["claims.yml#c001"],
            }],
        })
        assert errors_of(case) == []

    def test_final_mitigated_with_dir_ref_fails(self, tmp_path):
        case, signal_id = severe_case(tmp_path, "final_under_uncertainty")
        write(case / "bias-response.yml", {
            "schema_version": "1.0",
            "case_ref": "cases/severe",
            "responses": [{
                "signal_ref": signal_id,
                "response_status": "mitigated",
                "rationale": "references the case directory itself",
                "mitigation_refs": ["."],
            }],
        })
        assert errors_of(case)

    def test_final_mitigated_with_nonexistent_ref_fails(self, tmp_path):
        case, signal_id = severe_case(tmp_path, "final_under_uncertainty")
        write(case / "bias-response.yml", {
            "schema_version": "1.0",
            "case_ref": "cases/severe",
            "responses": [{
                "signal_ref": signal_id,
                "response_status": "mitigated",
                "rationale": "claims to have fixed a file that is not there",
                "mitigation_refs": ["does-not-exist.yml"],
            }],
        })
        assert errors_of(case)

    def test_final_unknown_signal_ref_fails(self, tmp_path):
        case, _ = severe_case(tmp_path, "final_under_uncertainty")
        write(case / "bias-response.yml", {
            "schema_version": "1.0",
            "case_ref": "cases/severe",
            "responses": [{
                "signal_ref": "bs_000000000000",
                "response_status": "false_positive",
                "rationale": "irrelevant",
                "mitigation_refs": ["claims.yml"],
            }],
        })
        errs = errors_of(case)
        assert any("not generated" in e for e in errs)

    def test_wrong_case_ref_fails(self, tmp_path):
        case, signal_id = severe_case(tmp_path, "final_under_uncertainty")
        write(case / "bias-response.yml", {
            "schema_version": "1.0",
            "case_ref": "cases/wrong/path",
            "responses": [{
                "signal_ref": signal_id,
                "response_status": "mitigated",
                "rationale": "fixed the language",
                "mitigation_refs": ["assessment.md"],
            }],
        })
        errs = errors_of(case)
        assert any("case_ref" in e for e in errs)

    def test_severe_signal_accepted_with_constraint_fails(self, tmp_path):
        case, signal_id = severe_case(tmp_path, "final_under_uncertainty")
        write(case / "bias-response.yml", {
            "schema_version": "1.0",
            "case_ref": "cases/severe",
            "responses": [{
                "signal_ref": signal_id,
                "response_status": "accepted_with_constraint",
                "rationale": "we will just live with it",
                "residual_risk": 0.4,
                "constraint_statement": "bounded to the discourse layer",
                "mitigation_refs": ["claims.yml"],
            }],
        })
        errs = errors_of(case)
        assert any("cannot be discharged" in e for e in errs)


class TestAcceptedWithConstraintRules:
    def test_accepted_without_residual_risk_fails(self, tmp_path):
        case, signal_id = soft_case(tmp_path, "final_under_uncertainty")
        write(case / "bias-response.yml", {
            "schema_version": "1.0",
            "case_ref": "cases/soft",
            "responses": [{
                "signal_ref": signal_id,
                "response_status": "accepted_with_constraint",
                "rationale": "bounded but unmeasured",
                "constraint_statement": "only applies to one comparison",
                "mitigation_refs": ["claims.yml"],
            }],
        })
        errs = errors_of(case)
        assert any("residual_risk" in e for e in errs)

    def test_accepted_with_full_fields_passes(self, tmp_path):
        case, signal_id = soft_case(tmp_path, "final_under_uncertainty")
        write(case / "bias-response.yml", {
            "schema_version": "1.0",
            "case_ref": "cases/soft",
            "responses": [{
                "signal_ref": signal_id,
                "response_status": "accepted_with_constraint",
                "rationale": "comparison base is implicit but documented downstream",
                "residual_risk": 0.3,
                "constraint_statement": "claim only ranks two named alternatives",
                "mitigation_refs": ["claims.yml"],
            }],
        })
        assert errors_of(case) == []
