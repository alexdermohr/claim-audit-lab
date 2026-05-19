"""Tests for scripts/validate_answer_receipt_claims_consistency.py."""

import pathlib
import sys
import textwrap

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_answer_receipt_claims_consistency


def _write_case(tmp_path, claims_yaml, receipt_yaml, *, path=("history", "case-a"), include_assessment=True):
    case_dir = tmp_path / "cases"
    for part in path:
        case_dir /= part
    case_dir.mkdir(parents=True)
    (case_dir / "claims.yml").write_text(claims_yaml, encoding="utf-8")
    (case_dir / "answer-receipt.yml").write_text(receipt_yaml, encoding="utf-8")
    (case_dir / "sources.yml").write_text('schema_version: "1.0"\nsources: []\n', encoding="utf-8")
    if include_assessment:
        (case_dir / "assessment.md").write_text("# Assessment\n", encoding="utf-8")
    return case_dir


def _claims(status: str = "established", claim_type: str = "factual_event_claim") -> str:
    return textwrap.dedent(
        f"""
        schema_version: "1.0"
        claims:
          - schema_version: "1.0"
            claim_id: "c001"
            claim_type: "{claim_type}"
            statement: "Claim statement"
            status: "{status}"
            uncertainty:
              score: 0.2
              causes: ["x"]
            interpolation:
              score: 0.1
              assumptions: ["y"]
        """
    ).strip() + "\n"


def _receipt(verdicts_block: str, *, background_only: bool = False, task: str = "case_building") -> str:
    indented_verdicts = "\n".join(f"  {line}" if line.strip() else line for line in verdicts_block.splitlines())
    bg_line = "  background_knowledge_only: true\n" if background_only else ""
    return (
        'schema_version: "1.0"\n'
        'question: "q"\n'
        f"task_classification: {task}\n"
        'answer_summary: "Not a truth certificate."\n'
        "verdicts_used:\n"
        f"{indented_verdicts}\n"
        "counterhypotheses_considered: []\n"
        "forbidden_upgrades_check:\n"
        "  upgrades_considered: []\n"
        "  upgrades_blocked: []\n"
        "banned_phrases_self_scan:\n"
        "  scanned: true\n"
        "  hits: []\n"
        "source_cluster_audit:\n"
        "  clusters_identified: []\n"
        "  independence_verified: true\n"
        "refusal_check:\n"
        "  refused: false\n"
        "external_research:\n"
        "  tools_used: []\n"
        "  sources_consulted: []\n"
        f"{bg_line}"
        "oracle_disclaimer_present: true\n"
        'final_uncertainty_statement: "background-knowledge-only, no external verification; not a truth certificate."\n'
        'what_would_change_assessment: "More evidence."\n'
    )


def test_claims_established_receipt_empty_fails(tmp_path):
    _write_case(
        tmp_path,
        _claims(status="established"),
        _receipt("  []"),
    )
    assert validate_answer_receipt_claims_consistency.main(str(tmp_path / "cases")) == 1


def test_claim_status_mismatch_fails(tmp_path):
    _write_case(
        tmp_path,
        _claims(status="established"),
        _receipt(
            textwrap.dedent(
                """
                  - claim_id: "c001"
                    statement: "Claim statement"
                    status: "plausible"
                """
            ).rstrip()
        ),
    )
    assert validate_answer_receipt_claims_consistency.main(str(tmp_path / "cases")) == 1


def test_unknown_claim_id_in_receipt_fails(tmp_path):
    _write_case(
        tmp_path,
        _claims(status="established"),
        _receipt(
            textwrap.dedent(
                """
                  - claim_id: "c999"
                    statement: "Unknown claim"
                    status: "established"
                """
            ).rstrip()
        ),
    )
    assert validate_answer_receipt_claims_consistency.main(str(tmp_path / "cases")) == 1


def test_matching_weak_claim_passes(tmp_path):
    _write_case(
        tmp_path,
        _claims(status="weak"),
        _receipt(
            textwrap.dedent(
                """
                  - claim_id: "c001"
                    statement: "Claim statement"
                    status: "weak"
                """
            ).rstrip()
        ),
    )
    assert validate_answer_receipt_claims_consistency.main(str(tmp_path / "cases")) == 0


def test_background_only_with_strong_causal_fails(tmp_path):
    _write_case(
        tmp_path,
        _claims(status="strongly_supported", claim_type="causal_claim"),
        _receipt(
            textwrap.dedent(
                """
                  - claim_id: "c001"
                    statement: "Claim statement"
                    status: "strongly_supported"
                """
            ).rstrip(),
            background_only=True,
        ),
    )
    assert validate_answer_receipt_claims_consistency.main(str(tmp_path / "cases")) == 1


def test_sandbox_case_can_keep_empty_verdicts(tmp_path):
    _write_case(
        tmp_path,
        _claims(status="plausible"),
        _receipt("  []"),
        path=("sandbox", "fixture"),
    )
    assert validate_answer_receipt_claims_consistency.main(str(tmp_path / "cases")) == 0
