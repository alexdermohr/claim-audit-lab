"""Tests for scripts/validate_answer_receipt.py."""

import pathlib
import sys
import textwrap

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_answer_receipt


def _make_case_with_receipt(tmp_path, receipt_yaml, name="case-a"):
    case_dir = tmp_path / "cases" / "history" / name
    case_dir.mkdir(parents=True)
    (case_dir / "claims.yml").write_text("claims: []\n", encoding="utf-8")
    (case_dir / "answer-receipt.yml").write_text(receipt_yaml, encoding="utf-8")
    return case_dir


def _make_case_without_receipt(tmp_path, name="case-no-receipt"):
    case_dir = tmp_path / "cases" / "history" / name
    case_dir.mkdir(parents=True)
    (case_dir / "claims.yml").write_text("claims: []\n", encoding="utf-8")
    return case_dir


VALID_RECEIPT = textwrap.dedent("""
schema_version: "1.0"
question: "Test question?"
task_classification: claim_audit
answer_summary: "Test answer. Not a truth certificate."
verdicts_used:
  - claim_id: "c001"
    statement: "Test statement"
    status: "plausible"
    uncertainty_score: 0.3
counterhypotheses_considered:
  - statement: "alternative reading"
    steelman_quality: 0.6
forbidden_upgrades_check:
  upgrades_considered: ["correlation_to_causation"]
  upgrades_blocked: ["correlation_to_causation"]
banned_phrases_self_scan:
  scanned: true
  hits: []
source_cluster_audit:
  clusters_identified: []
  independence_verified: true
refusal_check:
  refused: false
external_research:
  tools_used: ["web"]
  sources_consulted: []
oracle_disclaimer_present: true
final_uncertainty_statement: "Background and tooling notes; not a truth certificate."
what_would_change_assessment: "Additional primary sources."
""").strip()


def test_valid_receipt_passes(tmp_path):
    _make_case_with_receipt(tmp_path, VALID_RECEIPT)
    assert validate_answer_receipt.main(str(tmp_path / "cases")) == 0


def test_missing_required_field_fails(tmp_path):
    receipt = VALID_RECEIPT.replace(
        'oracle_disclaimer_present: true', ""
    )
    _make_case_with_receipt(tmp_path, receipt)
    assert validate_answer_receipt.main(str(tmp_path / "cases")) == 1


def test_missing_oracle_disclaimer_fails(tmp_path):
    receipt = VALID_RECEIPT.replace(
        'oracle_disclaimer_present: true',
        'oracle_disclaimer_present: false',
    )
    _make_case_with_receipt(tmp_path, receipt)
    assert validate_answer_receipt.main(str(tmp_path / "cases")) == 1


def test_strong_verdict_without_independence_fails(tmp_path):
    receipt = VALID_RECEIPT.replace(
        'status: "plausible"',
        'status: "established"',
    ).replace(
        'independence_verified: true',
        'independence_verified: false',
    )
    _make_case_with_receipt(tmp_path, receipt)
    assert validate_answer_receipt.main(str(tmp_path / "cases")) == 1


def test_strong_verdict_with_high_fragility_passes(tmp_path):
    receipt = VALID_RECEIPT.replace(
        'status: "plausible"',
        'status: "established"',
    ).replace(
        'independence_verified: true',
        'independence_verified: false\n  fragility_score: 0.85',
    )
    _make_case_with_receipt(tmp_path, receipt)
    # Strong verdict with declared fragility >= 0.7 is permitted by the
    # source-cluster-independence check, but still need upgrades_considered
    # populated and counterhypotheses for causal-looking statements.
    # statement is not causal-looking, so counterhypotheses check is loose.
    assert validate_answer_receipt.main(str(tmp_path / "cases")) == 0


def test_strong_verdict_without_upgrades_considered_fails(tmp_path):
    receipt = VALID_RECEIPT.replace(
        'status: "plausible"',
        'status: "established"',
    ).replace(
        'upgrades_considered: ["correlation_to_causation"]',
        'upgrades_considered: []',
    )
    _make_case_with_receipt(tmp_path, receipt)
    assert validate_answer_receipt.main(str(tmp_path / "cases")) == 1


def test_no_external_tools_without_background_only_label_fails(tmp_path):
    receipt = VALID_RECEIPT.replace(
        'tools_used: ["web"]',
        'tools_used: []',
    )
    _make_case_with_receipt(tmp_path, receipt)
    assert validate_answer_receipt.main(str(tmp_path / "cases")) == 1


def test_background_only_label_present_passes(tmp_path):
    receipt = VALID_RECEIPT.replace(
        'tools_used: ["web"]',
        'tools_used: []\n  background_knowledge_only: true',
    ).replace(
        'final_uncertainty_statement: "Background and tooling notes; not a truth certificate."',
        'final_uncertainty_statement: "background-knowledge-only, no external verification; not a truth certificate."',
    )
    _make_case_with_receipt(tmp_path, receipt)
    assert validate_answer_receipt.main(str(tmp_path / "cases")) == 0


def test_refusal_with_controversy_marker_fails(tmp_path):
    receipt = VALID_RECEIPT.replace(
        'refused: false',
        'refused: true\n  refusal_type: missing_evidence',
    ).replace(
        'final_uncertainty_statement: "Background and tooling notes; not a truth certificate."',
        'final_uncertainty_statement: "This is a controversial topic; not a truth certificate."',
    )
    _make_case_with_receipt(tmp_path, receipt)
    assert validate_answer_receipt.main(str(tmp_path / "cases")) == 1


def test_causal_verdict_without_counterhypotheses_fails(tmp_path):
    receipt = VALID_RECEIPT.replace(
        'status: "plausible"',
        'status: "strongly_supported"',
    ).replace(
        'statement: "Test statement"',
        'statement: "X caused Y in the documented channels"',
    ).replace(
        '- statement: "alternative reading"\n    steelman_quality: 0.6',
        '',
    ).replace(
        'counterhypotheses_considered:\n  ',
        'counterhypotheses_considered: []\n# ',
    )
    _make_case_with_receipt(tmp_path, receipt)
    assert validate_answer_receipt.main(str(tmp_path / "cases")) == 1


def test_answer_summary_too_long_fails(tmp_path):
    long_answer = "x" * 700
    receipt = VALID_RECEIPT.replace(
        'answer_summary: "Test answer. Not a truth certificate."',
        f'answer_summary: "{long_answer}"',
    )
    _make_case_with_receipt(tmp_path, receipt)
    assert validate_answer_receipt.main(str(tmp_path / "cases")) == 1


def test_missing_receipt_fails_when_assessment_exists(tmp_path):
    case_dir = _make_case_without_receipt(tmp_path, "case-assessment")
    (case_dir / "assessment.md").write_text("# Assessment\n", encoding="utf-8")
    assert validate_answer_receipt.main(str(tmp_path / "cases")) == 1


def test_missing_receipt_fails_when_lifecycle_non_draft(tmp_path):
    case_dir = _make_case_without_receipt(tmp_path, "case-lifecycle")
    (case_dir / "lifecycle.yml").write_text(
        textwrap.dedent("""
        schema_version: "1.0"
        status: "provisional_under_uncertainty"
        """).strip() + "\n",
        encoding="utf-8",
    )
    assert validate_answer_receipt.main(str(tmp_path / "cases")) == 1


def test_missing_receipt_passes_for_draft_without_assessment(tmp_path):
    case_dir = _make_case_without_receipt(tmp_path, "case-draft")
    (case_dir / "lifecycle.yml").write_text(
        textwrap.dedent("""
        schema_version: "1.0"
        status: "draft"
        """).strip() + "\n",
        encoding="utf-8",
    )
    assert validate_answer_receipt.main(str(tmp_path / "cases")) == 0


def test_missing_evidence_requires_refused_false(tmp_path):
    receipt = VALID_RECEIPT.replace(
        'refused: false',
        'refused: true\n  refusal_type: missing_evidence',
    ).replace(
        'status: "plausible"',
        'status: "no_verdict_possible"',
    )
    _make_case_with_receipt(tmp_path, receipt)
    assert validate_answer_receipt.main(str(tmp_path / "cases")) == 1


def test_missing_evidence_with_refused_false_and_unresolved_verdict_passes(tmp_path):
    receipt = VALID_RECEIPT.replace(
        'status: "plausible"',
        'status: "no_verdict_possible"',
    ).replace(
        'refused: false',
        'refused: false\n  refusal_type: missing_evidence',
    )
    _make_case_with_receipt(tmp_path, receipt)
    assert validate_answer_receipt.main(str(tmp_path / "cases")) == 0
