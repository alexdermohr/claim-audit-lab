#!/usr/bin/env python3
"""
Tests for validate_reported_claim_world_effect.py
"""

import pytest
import tempfile
from pathlib import Path
import yaml
import subprocess
import sys


@pytest.fixture
def case_dir(tmp_path):
    """Create a temporary case directory."""
    case = tmp_path / "test_case"
    case.mkdir()
    return case


def write_yml_file(case_dir: Path, filename: str, data: dict):
    """Write a YAML file to a case directory."""
    file_path = case_dir / filename
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)


def run_validator(cases_dir: Path) -> tuple[int, str]:
    """Run the validator and return exit code and output."""
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_reported_claim_world_effect.py",
            str(cases_dir),
        ],
        cwd="/home/alex/repos/claim-audit-lab",
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


class TestReportedClaimWorldEffect:
    """Tests for reported claim world-effect validation."""

    def test_reported_claim_as_strong_alternative_explanation_fails(self, tmp_path):
        """Fail: report-derived evidence as strong alternative_explanation without provenance."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {
            "claims": [
                {
                    "claim_id": "c001",
                    "statement": "The building collapsed due to controlled demolition",
                    "claim_type": "causal_claim",
                    "claim_kind": "causal_claim",
                },
                {
                    "claim_id": "c002",
                    "statement": "NIST reported fire-induced collapse",
                    "claim_type": "causal_claim",
                    "claim_kind": "reported_claim",
                },
            ]
        }

        evidence_data = {
            "evidence": [
                {
                    "evidence_id": "e001",
                    "evidence_type": "source_document",
                    "claim_refs": ["c002"],
                    "source_refs": ["s001"],
                }
            ]
        }

        relations_data = {
            "relations": [
                {
                    "relation_id": "r001",
                    "claim_ref": "c001",
                    "evidence_refs": ["e001"],
                    "relation_type": "alternative_explanation",
                    "strength": 0.74,
                }
            ]
        }

        write_yml_file(case_dir, "claims.yml", claims_data)
        write_yml_file(case_dir, "evidence-pack.yml", evidence_data)
        write_yml_file(case_dir, "evidence-relations.yml", relations_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "r001" in output
        assert "alternative_explanation" in output

    def test_reported_claim_as_safe_relation_passes(self, tmp_path):
        """Pass: report-derived evidence as safe relation (reports)."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {
            "claims": [
                {
                    "claim_id": "c001",
                    "statement": "Something happened",
                    "claim_type": "causal_claim",
                },
                {
                    "claim_id": "c002",
                    "statement": "NIST reported X",
                    "claim_kind": "reported_claim",
                },
            ]
        }

        evidence_data = {
            "evidence": [
                {
                    "evidence_id": "e001",
                    "evidence_type": "source_document",
                    "claim_refs": ["c002"],
                    "source_refs": ["s001"],
                }
            ]
        }

        relations_data = {
            "relations": [
                {
                    "relation_id": "r001",
                    "claim_ref": "c001",
                    "evidence_refs": ["e001"],
                    "relation_type": "reports",
                    "strength": 0.8,
                }
            ]
        }

        write_yml_file(case_dir, "claims.yml", claims_data)
        write_yml_file(case_dir, "evidence-pack.yml", evidence_data)
        write_yml_file(case_dir, "evidence-relations.yml", relations_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 0

    def test_weak_reported_claim_alternative_explanation_passes(self, tmp_path):
        """Pass: report-derived evidence as alternative_explanation but strength < 0.6."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {
            "claims": [
                {"claim_id": "c001", "statement": "X", "claim_type": "causal_claim"},
                {
                    "claim_id": "c002",
                    "statement": "NIST said Y",
                    "claim_kind": "reported_claim",
                },
            ]
        }

        evidence_data = {
            "evidence": [
                {
                    "evidence_id": "e001",
                    "claim_refs": ["c002"],
                    "source_refs": ["s001"],
                }
            ]
        }

        relations_data = {
            "relations": [
                {
                    "relation_id": "r001",
                    "claim_ref": "c001",
                    "evidence_refs": ["e001"],
                    "relation_type": "alternative_explanation",
                    "strength": 0.45,
                }
            ]
        }

        write_yml_file(case_dir, "claims.yml", claims_data)
        write_yml_file(case_dir, "evidence-pack.yml", evidence_data)
        write_yml_file(case_dir, "evidence-relations.yml", relations_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 0

    def test_reported_claim_strong_alternative_with_inference_provenance_passes(
        self, tmp_path
    ):
        """Pass: strong alternative_explanation with inference-ledger handling."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {
            "claims": [
                {
                    "claim_id": "c001",
                    "statement": "Controlled demolition",
                    "claim_type": "causal_claim",
                },
                {
                    "claim_id": "c002",
                    "statement": "NIST reported fire collapse",
                    "claim_kind": "reported_claim",
                },
            ]
        }

        evidence_data = {
            "evidence": [
                {
                    "evidence_id": "e001",
                    "claim_refs": ["c002"],
                    "source_refs": ["s001"],
                }
            ]
        }

        relations_data = {
            "relations": [
                {
                    "relation_id": "r001",
                    "claim_ref": "c001",
                    "evidence_refs": ["e001"],
                    "relation_type": "alternative_explanation",
                    "strength": 0.74,
                }
            ]
        }

        inference_data = {
            "inferences": [
                {
                    "claim_ref": "c001",
                    "premise_claim_refs": ["c002"],
                    "forbidden_upgrades_checked": ["reported_to_world"],
                    "inference_type": "direct_premise",
                }
            ]
        }

        write_yml_file(case_dir, "claims.yml", claims_data)
        write_yml_file(case_dir, "evidence-pack.yml", evidence_data)
        write_yml_file(case_dir, "evidence-relations.yml", relations_data)
        write_yml_file(case_dir, "inference-ledger.yml", inference_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 0

    def test_reported_claim_strong_weakens_without_inference_fails(self, tmp_path):
        """Fail: strong weakens relation without inference provenance."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {
            "claims": [
                {"claim_id": "c001", "statement": "X", "claim_type": "causal_claim"},
                {"claim_id": "c002", "statement": "Y", "claim_kind": "reported_claim"},
            ]
        }

        evidence_data = {
            "evidence": [
                {
                    "evidence_id": "e001",
                    "claim_refs": ["c002"],
                }
            ]
        }

        relations_data = {
            "relations": [
                {
                    "relation_id": "r001",
                    "claim_ref": "c001",
                    "evidence_refs": ["e001"],
                    "relation_type": "weakens",
                    "strength": 0.65,
                }
            ]
        }

        write_yml_file(case_dir, "claims.yml", claims_data)
        write_yml_file(case_dir, "evidence-pack.yml", evidence_data)
        write_yml_file(case_dir, "evidence-relations.yml", relations_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1

    def test_reported_claim_strong_supports_directly_without_provenance_fails(
        self, tmp_path
    ):
        """Fail: strong supports_directly from reported claim without provenance."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {
            "claims": [
                {
                    "claim_id": "c001",
                    "statement": "Fire caused collapse",
                    "claim_type": "causal_claim",
                },
                {
                    "claim_id": "c002",
                    "statement": "Expert report X",
                    "claim_kind": "reported_claim",
                },
            ]
        }

        evidence_data = {
            "evidence": [
                {
                    "evidence_id": "e001",
                    "claim_refs": ["c002"],
                }
            ]
        }

        relations_data = {
            "relations": [
                {
                    "relation_id": "r001",
                    "claim_ref": "c001",
                    "evidence_refs": ["e001"],
                    "relation_type": "supports_directly",
                    "strength": 0.7,
                }
            ]
        }

        write_yml_file(case_dir, "claims.yml", claims_data)
        write_yml_file(case_dir, "evidence-pack.yml", evidence_data)
        write_yml_file(case_dir, "evidence-relations.yml", relations_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1

    def test_non_world_claim_target_not_checked(self, tmp_path):
        """Pass: report-derived evidence against non-world claim target."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {
            "claims": [
                {
                    "claim_id": "c001",
                    "statement": "Meta claim",
                    "claim_kind": "meta_claim",
                },
                {
                    "claim_id": "c002",
                    "statement": "Reported X",
                    "claim_kind": "reported_claim",
                },
            ]
        }

        evidence_data = {
            "evidence": [
                {
                    "evidence_id": "e001",
                    "claim_refs": ["c002"],
                }
            ]
        }

        relations_data = {
            "relations": [
                {
                    "relation_id": "r001",
                    "claim_ref": "c001",
                    "evidence_refs": ["e001"],
                    "relation_type": "supports_directly",
                    "strength": 0.9,
                }
            ]
        }

        write_yml_file(case_dir, "claims.yml", claims_data)
        write_yml_file(case_dir, "evidence-pack.yml", evidence_data)
        write_yml_file(case_dir, "evidence-relations.yml", relations_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 0

    def test_empty_cases_passes(self, tmp_path):
        """Pass: no evidence-relations files."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {"claims": []}
        write_yml_file(case_dir, "claims.yml", claims_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 0

    def test_comparative_claim_as_target_is_checked(self, tmp_path):
        """Fail: report-derived evidence as strong effect against comparative_claim."""
        case_dir = tmp_path / "test_case"
        case_dir.mkdir()

        claims_data = {
            "claims": [
                {
                    "claim_id": "c001",
                    "statement": "P(A) > P(B)",
                    "claim_kind": "comparative_claim",
                },
                {
                    "claim_id": "c002",
                    "statement": "Report says otherwise",
                    "claim_kind": "reported_claim",
                },
            ]
        }

        evidence_data = {
            "evidence": [
                {
                    "evidence_id": "e001",
                    "claim_refs": ["c002"],
                }
            ]
        }

        relations_data = {
            "relations": [
                {
                    "relation_id": "r001",
                    "claim_ref": "c001",
                    "evidence_refs": ["e001"],
                    "relation_type": "contradicts_directly",
                    "strength": 0.8,
                }
            ]
        }

        write_yml_file(case_dir, "claims.yml", claims_data)
        write_yml_file(case_dir, "evidence-pack.yml", evidence_data)
        write_yml_file(case_dir, "evidence-relations.yml", relations_data)

        exit_code, output = run_validator(tmp_path)
        assert exit_code == 1
        assert "contradicts_directly" in output
