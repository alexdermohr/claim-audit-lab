#!/usr/bin/env python3
"""Tests for validate_reported_claim_world_effect.py."""

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def case_dir(tmp_path):
    case = tmp_path / "test_case"
    case.mkdir()
    return case


def write_yml_file(case_dir: Path, filename: str, data: dict):
    with open(case_dir / filename, "w", encoding="utf-8") as f:
        yaml.dump(data, f)


def run_validator(cases_dir: Path) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, "scripts/validate_reported_claim_world_effect.py", str(cases_dir)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


class TestReportedClaimWorldEffect:
    def test_reported_claim_as_strong_alternative_explanation_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "The building collapsed due to controlled demolition", "claim_type": "causal_claim", "claim_kind": "causal_claim"},
            {"claim_id": "c002", "statement": "NIST reported fire-induced collapse", "claim_type": "causal_claim", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [
            {"evidence_id": "e001", "evidence_type": "source_document", "claim_refs": ["c002"], "source_refs": ["s001"]}
        ]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r001", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "alternative_explanation", "strength": 0.74}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "r001" in output
        assert "alternative_explanation" in output

    def test_reported_claim_as_safe_relation_passes(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "Something happened", "claim_type": "causal_claim"},
            {"claim_id": "c002", "statement": "NIST reported X", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [
            {"evidence_id": "e001", "evidence_type": "source_document", "claim_refs": ["c002"], "source_refs": ["s001"]}
        ]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r001", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "reports", "strength": 0.8}
        ]})
        exit_code, _ = run_validator(tmp_path)
        assert exit_code == 0

    def test_weak_reported_claim_alternative_explanation_passes(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "X", "claim_type": "causal_claim"},
            {"claim_id": "c002", "statement": "NIST said Y", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [
            {"evidence_id": "e001", "claim_refs": ["c002"], "source_refs": ["s001"]}
        ]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r001", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "alternative_explanation", "strength": 0.45}
        ]})
        exit_code, _ = run_validator(tmp_path)
        assert exit_code == 0

    def test_reported_claim_strong_alternative_with_inference_provenance_passes(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "Controlled demolition", "claim_type": "causal_claim"},
            {"claim_id": "c002", "statement": "NIST reported fire collapse", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [
            {"evidence_id": "e001", "claim_refs": ["c002"], "source_refs": ["s001"]}
        ]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r001", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "alternative_explanation", "strength": 0.74}
        ]})
        write_yml_file(case_dir, "inference-ledger.yml", {"inferences": [
            {"claim_ref": "c001", "premise_claim_refs": ["c002"], "forbidden_upgrades_checked": ["reported_to_world"], "inference_type": "direct_premise"}
        ]})
        exit_code, _ = run_validator(tmp_path)
        assert exit_code == 0

    def test_reported_claim_strong_weakens_without_inference_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "X", "claim_type": "causal_claim"},
            {"claim_id": "c002", "statement": "Y", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [{"evidence_id": "e001", "claim_refs": ["c002"]}]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r001", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "weakens", "strength": 0.65}
        ]})
        exit_code, _ = run_validator(tmp_path)
        assert exit_code == 1

    def test_reported_claim_strong_supports_directly_without_provenance_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "Fire caused collapse", "claim_type": "causal_claim"},
            {"claim_id": "c002", "statement": "Expert report X", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [{"evidence_id": "e001", "claim_refs": ["c002"]}]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r001", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "supports_directly", "strength": 0.7}
        ]})
        exit_code, _ = run_validator(tmp_path)
        assert exit_code == 1

    def test_non_world_claim_target_not_checked(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "Meta claim", "claim_kind": "meta_claim"},
            {"claim_id": "c002", "statement": "Reported X", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [{"evidence_id": "e001", "claim_refs": ["c002"]}]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r001", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "supports_directly", "strength": 0.9}
        ]})
        exit_code, _ = run_validator(tmp_path)
        assert exit_code == 0

    def test_empty_cases_passes(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": []})
        exit_code, _ = run_validator(tmp_path)
        assert exit_code == 0

    def test_comparative_claim_as_target_is_checked(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "P(A) > P(B)", "claim_kind": "comparative_claim"},
            {"claim_id": "c002", "statement": "Report says otherwise", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [{"evidence_id": "e001", "claim_refs": ["c002"]}]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r001", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "contradicts_directly", "strength": 0.8}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "contradicts_directly" in output

    def test_singular_evidence_ref_fails_without_provenance(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "Controlled demolition caused collapse", "claim_kind": "causal_claim"},
            {"claim_id": "c002", "statement": "NIST reported fire collapse", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [{"evidence_id": "e001", "claim_refs": ["c002"]}]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r001", "claim_ref": "c001", "evidence_ref": "e001", "relation_type": "alternative_explanation", "strength": 0.74}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "r001" in output
        assert "alternative_explanation" in output

    def test_nested_inference_steps_with_singular_forbidden_upgrade_passes(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "Controlled demolition", "claim_kind": "causal_claim"},
            {"claim_id": "c002", "statement": "NIST reported fire collapse", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [{"evidence_id": "e001", "claim_refs": ["c002"]}]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r001", "claim_ref": "c001", "evidence_ref": "e001", "relation_type": "alternative_explanation", "strength": 0.74}
        ]})
        write_yml_file(case_dir, "inference-ledger.yml", {"inferences": [
            {"inference_id": "inf001", "claim_ref": "c001", "triggered_by": "strong_positive_verdict", "inference_steps": [
                {"step_id": "step001", "premise_claim_refs": ["c002"], "operation": "corroboration", "produces": "NIST engineering assessment used as world argument with justification", "forbidden_upgrade_checked": ["reported_to_world"]}
            ]}
        ]})
        exit_code, _ = run_validator(tmp_path)
        assert exit_code == 0

    def test_argument_provenance_passes_for_non_major_relation(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "Controlled demolition", "claim_kind": "causal_claim"},
            {"claim_id": "c002", "statement": "NIST reported fire collapse", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [{"evidence_id": "e001", "claim_refs": ["c002"]}]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r001", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "alternative_explanation", "strength": 0.62}
        ]})
        write_yml_file(case_dir, "argument-provenance.yml", {"arguments": [
            {"argument_id": "arg001", "target_claim_ref": "c001", "premise_claim_refs": ["c002"], "role": "non_decisive_defeater", "allowed_effect": "non_decisive", "forbidden_upgrades_checked": ["reported_to_world"]}
        ]})
        exit_code, _ = run_validator(tmp_path)
        assert exit_code == 0

    def test_argument_provenance_major_with_empty_independent_support_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "Controlled demolition", "claim_kind": "causal_claim"},
            {"claim_id": "c002", "statement": "NIST reported fire collapse", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [{"evidence_id": "e001", "claim_refs": ["c002"]}]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r001", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "alternative_explanation", "strength": 0.8}
        ]})
        write_yml_file(case_dir, "argument-provenance.yml", {"arguments": [
            {"argument_id": "arg001", "target_claim_ref": "c001", "premise_claim_refs": ["c002"], "role": "major_defeater", "allowed_effect": "major_with_independent_support", "forbidden_upgrades_checked": ["reported_to_world"], "independent_support_source_refs": []}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "r001" in output

    def test_inference_ledger_exists_but_missing_reported_to_world_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "Controlled demolition", "claim_kind": "causal_claim"},
            {"claim_id": "c002", "statement": "NIST reported fire collapse", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [{"evidence_id": "e001", "claim_refs": ["c002"]}]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r001", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "alternative_explanation", "strength": 0.74}
        ]})
        write_yml_file(case_dir, "inference-ledger.yml", {"inferences": [
            {"inference_id": "inf001", "claim_ref": "c001", "inference_steps": [
                {"step_id": "step001", "premise_claim_refs": ["c002"], "operation": "corroboration", "produces": "Some justification", "forbidden_upgrade_checked": ["source_prestige_to_truth"]}
            ]}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "r001" in output

    def test_supports_relation_without_provenance_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "World claim", "claim_kind": "causal_claim"},
            {"claim_id": "c002", "statement": "Reported claim", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [{"evidence_id": "e001", "claim_refs": ["c002"]}]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r_supports", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "supports", "strength": 0.7}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "r_supports" in output

    def test_contradicts_relation_without_provenance_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "World claim", "claim_kind": "causal_claim"},
            {"claim_id": "c002", "statement": "Reported claim", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [{"evidence_id": "e001", "claim_refs": ["c002"]}]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r_contradicts", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "contradicts", "strength": 0.7}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "r_contradicts" in output

    def test_major_relation_non_decisive_argument_provenance_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "Controlled demolition", "claim_kind": "causal_claim"},
            {"claim_id": "c002", "statement": "NIST reported fire collapse", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [{"evidence_id": "e001", "claim_refs": ["c002"]}]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r_major_fail", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "alternative_explanation", "strength": 0.8}
        ]})
        write_yml_file(case_dir, "argument-provenance.yml", {"arguments": [
            {"argument_id": "arg001", "target_claim_ref": "c001", "premise_claim_refs": ["c002"], "role": "non_decisive_defeater", "allowed_effect": "non_decisive", "forbidden_upgrades_checked": ["reported_to_world"]}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "r_major_fail" in output

    def test_major_relation_with_independent_support_passes(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "Controlled demolition", "claim_kind": "causal_claim"},
            {"claim_id": "c002", "statement": "NIST reported fire collapse", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [{"evidence_id": "e001", "claim_refs": ["c002"]}]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r_major_ok", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "alternative_explanation", "strength": 0.8}
        ]})
        write_yml_file(case_dir, "argument-provenance.yml", {"arguments": [
            {"argument_id": "arg001", "target_claim_ref": "c001", "premise_claim_refs": ["c002"], "role": "major_defeater", "allowed_effect": "major_with_independent_support", "forbidden_upgrades_checked": ["reported_to_world"], "independent_support_source_refs": ["s_independent"]}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 0, output

    def test_malformed_evidence_relations_yaml_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": []})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": []})
        (case_dir / "evidence-relations.yml").write_text("relations: [\n  - bad", encoding="utf-8")
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "evidence-relations.yml" in output
        assert "failed to parse YAML" in output

    def test_source_report_evidence_without_provenance_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "World claim", "claim_kind": "causal_claim"}
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [
            {"evidence_id": "e001", "burden_profile": "source_report", "source_refs": ["s001"]}
        ]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r_source_report", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "supports_directly", "strength": 0.7}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "r_source_report" in output

    def test_source_report_evidence_with_inference_passes(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "World claim", "claim_kind": "causal_claim"}
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [
            {"evidence_id": "e001", "burden_profile": "source_report", "source_refs": ["s001"]}
        ]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r_source_report_ok", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "supports_directly", "strength": 0.7}
        ]})
        write_yml_file(case_dir, "inference-ledger.yml", {"inferences": [
            {"claim_ref": "c001", "premise_evidence_refs": ["e001"], "forbidden_upgrades_checked": ["reported_to_world"]}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 0, output

    def test_string_strength_is_handled_deterministically(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "World claim", "claim_kind": "causal_claim"},
            {"claim_id": "c002", "statement": "Reported claim", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [
            {"evidence_id": "e001", "claim_refs": ["c002"]}
        ]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r_string_strength", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "supports", "strength": "0.7"}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "r_string_strength" in output


    def test_major_relation_inference_only_reported_to_world_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "World claim", "claim_kind": "causal_claim"},
            {"claim_id": "c002", "statement": "Reported claim", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [
            {"evidence_id": "e001", "claim_refs": ["c002"]}
        ]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r_inf_major_fail", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "alternative_explanation", "strength": 0.8}
        ]})
        write_yml_file(case_dir, "inference-ledger.yml", {"inferences": [
            {"claim_ref": "c001", "premise_claim_refs": ["c002"], "forbidden_upgrades_checked": ["reported_to_world"]}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "r_inf_major_fail" in output

    def test_major_relation_inference_with_independent_support_passes(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "World claim", "claim_kind": "causal_claim"},
            {"claim_id": "c002", "statement": "Reported claim", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [
            {"evidence_id": "e001", "claim_refs": ["c002"]}
        ]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r_inf_major_ok", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "alternative_explanation", "strength": 0.8}
        ]})
        write_yml_file(case_dir, "inference-ledger.yml", {"inferences": [
            {
                "claim_ref": "c001",
                "premise_claim_refs": ["c002"],
                "forbidden_upgrades_checked": ["reported_to_world"],
                "allowed_effect": "major_with_independent_support",
                "independent_support_source_refs": ["s_independent"],
            }
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 0, output

    def test_non_major_relation_inference_reported_to_world_passes(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "World claim", "claim_kind": "causal_claim"},
            {"claim_id": "c002", "statement": "Reported claim", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [
            {"evidence_id": "e001", "claim_refs": ["c002"]}
        ]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r_inf_non_major_ok", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "alternative_explanation", "strength": 0.62}
        ]})
        write_yml_file(case_dir, "inference-ledger.yml", {"inferences": [
            {"claim_ref": "c001", "premise_claim_refs": ["c002"], "forbidden_upgrades_checked": ["reported_to_world"]}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 0, output

    def test_multiple_markers_partial_provenance_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "World claim", "claim_kind": "causal_claim"},
            {"claim_id": "c002", "statement": "Reported 1", "claim_kind": "reported_claim"},
            {"claim_id": "c003", "statement": "Reported 2", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [
            {"evidence_id": "e001", "claim_refs": ["c002"]},
            {"evidence_id": "e002", "claim_refs": ["c003"]},
        ]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {
                "relation_id": "r_multi_partial_fail",
                "claim_ref": "c001",
                "evidence_refs": ["e001", "e002"],
                "relation_type": "supports",
                "strength": 0.7,
            }
        ]})
        write_yml_file(case_dir, "inference-ledger.yml", {"inferences": [
            {"claim_ref": "c001", "premise_claim_refs": ["c002"], "forbidden_upgrades_checked": ["reported_to_world"]}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "r_multi_partial_fail" in output

    def test_multiple_markers_all_provenance_passes(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "World claim", "claim_kind": "causal_claim"},
            {"claim_id": "c002", "statement": "Reported 1", "claim_kind": "reported_claim"},
            {"claim_id": "c003", "statement": "Reported 2", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [
            {"evidence_id": "e001", "claim_refs": ["c002"]},
            {"evidence_id": "e002", "claim_refs": ["c003"]},
        ]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {
                "relation_id": "r_multi_all_ok",
                "claim_ref": "c001",
                "evidence_refs": ["e001", "e002"],
                "relation_type": "supports",
                "strength": 0.7,
            }
        ]})
        write_yml_file(case_dir, "inference-ledger.yml", {"inferences": [
            {
                "claim_ref": "c001",
                "inference_steps": [
                    {"step_id": "s1", "premise_claim_refs": ["c002"], "forbidden_upgrades_checked": ["reported_to_world"]},
                    {"step_id": "s2", "premise_claim_refs": ["c003"], "forbidden_upgrades_checked": ["reported_to_world"]},
                ],
            }
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 0, output

    def test_source_report_with_inference_without_premise_evidence_refs_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "World claim", "claim_kind": "causal_claim"}
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [
            {"evidence_id": "e001", "burden_profile": "source_report", "source_refs": ["s001"]}
        ]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r_source_report_inference_fail", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "supports_directly", "strength": 0.7}
        ]})
        write_yml_file(case_dir, "inference-ledger.yml", {"inferences": [
            {"claim_ref": "c001", "forbidden_upgrades_checked": ["reported_to_world"]}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "r_source_report_inference_fail" in output

    def test_reports_relation_without_strength_is_ignored(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "World claim", "claim_kind": "causal_claim"},
            {"claim_id": "c002", "statement": "Reported", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [
            {"evidence_id": "e001", "claim_refs": ["c002"]}
        ]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r_reports_no_strength", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "reports"}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 0, output

    def test_supports_relation_without_strength_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "World claim", "claim_kind": "causal_claim"},
            {"claim_id": "c002", "statement": "Reported", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [
            {"evidence_id": "e001", "claim_refs": ["c002"]}
        ]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r_support_no_strength", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "supports"}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "r_support_no_strength" in output
        assert "strength must be numeric" in output

    def test_supports_relation_with_non_numeric_strength_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "World claim", "claim_kind": "causal_claim"},
            {"claim_id": "c002", "statement": "Reported", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [
            {"evidence_id": "e001", "claim_refs": ["c002"]}
        ]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r_support_bad_strength", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "supports", "strength": "abc"}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "r_support_bad_strength" in output
        assert "strength must be numeric" in output

    def test_legal_claim_target_is_checked(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "Legal claim", "claim_kind": "legal_claim"},
            {"claim_id": "c002", "statement": "Reported", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [
            {"evidence_id": "e001", "claim_refs": ["c002"]}
        ]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r_legal", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "supports", "strength": 0.7}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "r_legal" in output

    def test_suppression_claim_target_is_checked(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "Suppression claim", "claim_kind": "suppression_claim"},
            {"claim_id": "c002", "statement": "Reported", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [
            {"evidence_id": "e001", "claim_refs": ["c002"]}
        ]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": "r_suppression", "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "supports", "strength": 0.7}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "r_suppression" in output


    @pytest.mark.parametrize("claim_kind,relation_id", [
        ("capability_claim", "r_capability"),
        ("forecast_claim", "r_forecast"),
        ("value_claim", "r_value"),
        ("absence_claim", "r_absence"),
    ])
    def test_additional_world_claim_types_are_checked(self, tmp_path, claim_kind, relation_id):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_yml_file(case_dir, "claims.yml", {"claims": [
            {"claim_id": "c001", "statement": "World claim", "claim_kind": claim_kind},
            {"claim_id": "c002", "statement": "Reported", "claim_kind": "reported_claim"},
        ]})
        write_yml_file(case_dir, "evidence-pack.yml", {"evidence": [
            {"evidence_id": "e001", "claim_refs": ["c002"]}
        ]})
        write_yml_file(case_dir, "evidence-relations.yml", {"relations": [
            {"relation_id": relation_id, "claim_ref": "c001", "evidence_refs": ["e001"], "relation_type": "supports", "strength": 0.7}
        ]})
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert relation_id in output
