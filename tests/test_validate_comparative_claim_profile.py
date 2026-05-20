#!/usr/bin/env python3
"""Tests for validate_comparative_claim_profile.py."""

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


def write_claims_yml(case_dir: Path, claims_data: dict):
    claims_file = case_dir / "claims.yml"
    with open(claims_file, "w", encoding="utf-8") as f:
        yaml.dump(claims_data, f)


def run_validator(cases_dir: Path) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, "scripts/validate_comparative_claim_profile.py", str(cases_dir)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


class TestComparativeClaimProfile:
    def test_causal_claim_with_probability_language_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        claims_data = {
            "claims": [{
                "claim_id": "c001",
                "statement": "P(controlled demolition) > P(fire-induced collapse)",
                "claim_type": "causal_claim",
                "claim_kind": "causal_claim",
            }]
        }
        write_claims_yml(case_dir, claims_data)
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "c001" in output

    def test_causal_claim_with_wahrscheinlicher_als_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        claims_data = {
            "claims": [{
                "claim_id": "c002",
                "statement": "Die Sprengung ist wahrscheinlicher als der Brand",
                "claim_type": "causal_claim",
                "claim_kind": "causal_claim",
            }]
        }
        write_claims_yml(case_dir, claims_data)
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "c002" in output

    def test_comparative_claim_kind_passes(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        claims_data = {
            "claims": [{
                "claim_id": "c003",
                "statement": "P(A) > P(B)",
                "claim_type": "causal_claim",
                "claim_kind": "comparative_claim",
                "requires": ["comparative_probability"],
            }]
        }
        write_claims_yml(case_dir, claims_data)
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 0
        assert "valid" in output.lower()

    def test_comparative_burden_profile_passes(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        claims_data = {
            "claims": [{
                "claim_id": "c004",
                "statement": "More likely than the alternative",
                "claim_type": "causal_claim",
                "claim_kind": "causal_claim",
                "burden_profile": "comparative",
            }]
        }
        write_claims_yml(case_dir, claims_data)
        exit_code, _ = run_validator(tmp_path)
        assert exit_code == 0

    def test_normal_causal_claim_without_comparative_language_passes(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        claims_data = {
            "claims": [{
                "claim_id": "c005",
                "statement": "The fire caused the collapse",
                "claim_type": "causal_claim",
                "claim_kind": "causal_claim",
            }]
        }
        write_claims_yml(case_dir, claims_data)
        exit_code, _ = run_validator(tmp_path)
        assert exit_code == 0

    def test_comparative_language_in_notes_field(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        claims_data = {
            "claims": [{
                "claim_id": "c006",
                "statement": "Something happened",
                "notes": "The probability of A is higher than B",
                "claim_type": "causal_claim",
                "claim_kind": "causal_claim",
            }]
        }
        write_claims_yml(case_dir, claims_data)
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "c006" in output

    def test_multiple_claims_mixed(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        claims_data = {
            "claims": [
                {"claim_id": "c_ok", "statement": "Normal claim", "claim_type": "causal_claim", "claim_kind": "causal_claim"},
                {"claim_id": "c_fail", "statement": "P(X) > P(Y)", "claim_type": "causal_claim", "claim_kind": "causal_claim"},
            ]
        }
        write_claims_yml(case_dir, claims_data)
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "c_fail" in output
        assert "c_ok" not in output

    def test_empty_claims_file_passes(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        write_claims_yml(case_dir, {"claims": []})
        exit_code, _ = run_validator(tmp_path)
        assert exit_code == 0

    def test_no_claims_file_passes(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        exit_code, _ = run_validator(tmp_path)
        assert exit_code == 0

    def test_rather_than_uppercase_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        claims_data = {
            "claims": [{
                "claim_id": "c_case",
                "statement": "X RATHER THAN Y explains the data",
                "claim_type": "causal_claim",
                "claim_kind": "causal_claim",
            }]
        }
        write_claims_yml(case_dir, claims_data)
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "c_case" in output

    def test_comparative_claim_kind_without_comparative_probability_requirement_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        claims_data = {
            "claims": [{
                "claim_id": "c_req_fail",
                "statement": "P(A) > P(B)",
                "claim_kind": "comparative_claim",
                "requires": ["timeline", "mechanism"],
            }]
        }
        write_claims_yml(case_dir, claims_data)
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "c_req_fail" in output
        assert "comparative_probability" in output

    def test_burden_profile_comparative_passes_without_requires(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        claims_data = {
            "claims": [{
                "claim_id": "c_burden_ok",
                "statement": "More likely than the fire hypothesis",
                "claim_type": "causal_claim",
                "claim_kind": "causal_claim",
                "burden_profile": "comparative",
                "requires": [],
            }]
        }
        write_claims_yml(case_dir, claims_data)
        exit_code, _ = run_validator(tmp_path)
        assert exit_code == 0

    def test_comparative_claim_kind_with_comparative_probability_in_requires_passes(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        claims_data = {
            "claims": [{
                "claim_id": "c_req_ok",
                "statement": "P(A) > P(B)",
                "claim_kind": "comparative_claim",
                "requires": ["comparative_probability", "two_alternatives"],
            }]
        }
        write_claims_yml(case_dir, claims_data)
        exit_code, _ = run_validator(tmp_path)
        assert exit_code == 0

    def test_probability_is_high_statement_passes(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        claims_data = {
            "claims": [{
                "claim_id": "c_noncomp_de",
                "statement": "Die Wahrscheinlichkeit ist hoch, dass X geschah",
                "claim_type": "causal_claim",
                "claim_kind": "causal_claim",
            }]
        }
        write_claims_yml(case_dir, claims_data)
        exit_code, _ = run_validator(tmp_path)
        assert exit_code == 0

    def test_probability_is_high_english_statement_passes(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        claims_data = {
            "claims": [{
                "claim_id": "c_noncomp_en",
                "statement": "The probability is high that X occurred",
                "claim_type": "causal_claim",
                "claim_kind": "causal_claim",
            }]
        }
        write_claims_yml(case_dir, claims_data)
        exit_code, _ = run_validator(tmp_path)
        assert exit_code == 0

    def test_wahrscheinlichkeit_hoeher_als_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        claims_data = {
            "claims": [{
                "claim_id": "c_de_compare",
                "statement": "Die Wahrscheinlichkeit von X ist höher als Y",
                "claim_type": "causal_claim",
                "claim_kind": "causal_claim",
            }]
        }
        write_claims_yml(case_dir, claims_data)
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "c_de_compare" in output

    def test_p_expression_comparison_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        claims_data = {
            "claims": [{
                "claim_id": "c_p_compare",
                "statement": "P(X) > P(Y)",
                "claim_type": "causal_claim",
                "claim_kind": "causal_claim",
            }]
        }
        write_claims_yml(case_dir, claims_data)
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "c_p_compare" in output

    def test_rather_than_fails(self, tmp_path):
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()
        claims_data = {
            "claims": [{
                "claim_id": "c_rather_than",
                "statement": "X rather than Y explains the data",
                "claim_type": "causal_claim",
                "claim_kind": "causal_claim",
            }]
        }
        write_claims_yml(case_dir, claims_data)
        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "c_rather_than" in output
