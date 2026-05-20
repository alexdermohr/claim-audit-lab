#!/usr/bin/env python3
"""
Tests for validate_comparative_claim_profile.py
"""

import pytest
from pathlib import Path
import yaml
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def case_dir(tmp_path):
    """Create a temporary case directory."""
    case = tmp_path / "test_case"
    case.mkdir()
    return case


def write_claims_yml(case_dir: Path, claims_data: dict):
    """Write claims.yml to a case directory."""
    claims_file = case_dir / "claims.yml"
    with open(claims_file, "w", encoding="utf-8") as f:
        yaml.dump(claims_data, f)


def run_validator(cases_dir: Path) -> tuple[int, str]:
    """Run the validator and return exit code and output."""
    result = subprocess.run(
        [sys.executable, "scripts/validate_comparative_claim_profile.py", str(cases_dir)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


class TestComparativeClaimProfile:
    """Tests for comparative claim profile validation."""

    def test_causal_claim_with_probability_language_fails(self, tmp_path):
        """Fail: causal_claim with P(A) > P(B) language without comparative profile."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {
            "claims": [
                {
                    "claim_id": "c001",
                    "statement": "P(controlled demolition) > P(fire-induced collapse)",
                    "claim_type": "causal_claim",
                    "claim_kind": "causal_claim",
                    "burden_profile": None,
                }
            ]
        }
        write_claims_yml(case_dir, claims_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "c001" in output
        assert "comparative-language detected" in output
        assert "claim_kind" in output or "burden_profile" in output

    def test_causal_claim_with_wahrscheinlicher_als_fails(self, tmp_path):
        """Fail: causal_claim with 'wahrscheinlicher als' without comparative profile."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {
            "claims": [
                {
                    "claim_id": "c002",
                    "statement": "Die Sprengung ist wahrscheinlicher als der Brand",
                    "claim_type": "causal_claim",
                    "claim_kind": "causal_claim",
                }
            ]
        }
        write_claims_yml(case_dir, claims_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "c002" in output

    def test_comparative_claim_kind_passes(self, tmp_path):
        """Pass: claim_kind=comparative_claim with comparative_probability in requires."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {
            "claims": [
                {
                    "claim_id": "c003",
                    "statement": "P(A) > P(B)",
                    "claim_type": "causal_claim",
                    "claim_kind": "comparative_claim",
                    "requires": ["comparative_probability"],
                }
            ]
        }
        write_claims_yml(case_dir, claims_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 0
        assert "valid" in output.lower()

    def test_comparative_burden_profile_passes(self, tmp_path):
        """Pass: causal_claim with comparative language but burden_profile=comparative."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {
            "claims": [
                {
                    "claim_id": "c004",
                    "statement": "More likely than the alternative",
                    "claim_type": "causal_claim",
                    "claim_kind": "causal_claim",
                    "burden_profile": "comparative",
                }
            ]
        }
        write_claims_yml(case_dir, claims_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 0

    def test_normal_causal_claim_without_comparative_language_passes(self, tmp_path):
        """Pass: normal causal_claim without comparative language."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {
            "claims": [
                {
                    "claim_id": "c005",
                    "statement": "The fire caused the collapse",
                    "claim_type": "causal_claim",
                    "claim_kind": "causal_claim",
                }
            ]
        }
        write_claims_yml(case_dir, claims_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 0

    def test_comparative_language_in_notes_field(self, tmp_path):
        """Fail: comparative language in notes field."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {
            "claims": [
                {
                    "claim_id": "c006",
                    "statement": "Something happened",
                    "notes": "The probability of A is higher than B",
                    "claim_type": "causal_claim",
                    "claim_kind": "causal_claim",
                }
            ]
        }
        write_claims_yml(case_dir, claims_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "c006" in output

    def test_multiple_claims_mixed(self, tmp_path):
        """Mixed: some pass, one fails."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {
            "claims": [
                {
                    "claim_id": "c_ok",
                    "statement": "Normal claim",
                    "claim_type": "causal_claim",
                    "claim_kind": "causal_claim",
                },
                {
                    "claim_id": "c_fail",
                    "statement": "P(X) > P(Y)",
                    "claim_type": "causal_claim",
                    "claim_kind": "causal_claim",
                },
            ]
        }
        write_claims_yml(case_dir, claims_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "c_fail" in output
        assert "c_ok" not in output

    def test_empty_claims_file_passes(self, tmp_path):
        """Pass: no claims or empty claims list."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {"claims": []}
        write_claims_yml(case_dir, claims_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 0

    def test_no_claims_file_passes(self, tmp_path):
        """Pass: no claims.yml file."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 0

    def test_comparative_language_case_insensitive(self, tmp_path):
        """Fail: comparative language case-insensitive detection."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {
            "claims": [
                {
                    "claim_id": "c_case",
                    "statement": "PROBABILITY of A > PROBABILITY of B",
                    "claim_type": "causal_claim",
                    "claim_kind": "causal_claim",
                }
            ]
        }
        write_claims_yml(case_dir, claims_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "c_case" in output

    def test_comparative_claim_kind_without_comparative_probability_requirement_fails(self, tmp_path):
        """Fail: claim_kind=comparative_claim, requires missing comparative_probability, burden_profile not comparative."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {
            "claims": [
                {
                    "claim_id": "c_req_fail",
                    "statement": "P(A) > P(B)",
                    "claim_kind": "comparative_claim",
                    "requires": ["timeline", "mechanism"],  # no comparative_probability
                }
            ]
        }
        write_claims_yml(case_dir, claims_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "c_req_fail" in output
        assert "comparative_probability" in output

    def test_burden_profile_comparative_passes_without_requires(self, tmp_path):
        """Pass: burden_profile=comparative serves as declaration; no comparative_probability in requires needed."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {
            "claims": [
                {
                    "claim_id": "c_burden_ok",
                    "statement": "More likely than the fire hypothesis",
                    "claim_type": "causal_claim",
                    "claim_kind": "causal_claim",
                    "burden_profile": "comparative",
                    "requires": [],  # no comparative_probability — ok because burden_profile=comparative
                }
            ]
        }
        write_claims_yml(case_dir, claims_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 0

    def test_comparative_claim_kind_with_comparative_probability_in_requires_passes(self, tmp_path):
        """Pass: claim_kind=comparative_claim + requires=[comparative_probability]."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {
            "claims": [
                {
                    "claim_id": "c_req_ok",
                    "statement": "P(A) > P(B)",
                    "claim_kind": "comparative_claim",
                    "requires": ["comparative_probability", "two_alternatives"],
                }
            ]
        }
        write_claims_yml(case_dir, claims_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 0
