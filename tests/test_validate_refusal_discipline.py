"""Tests for scripts/validate_refusal_discipline.py."""

import pathlib
import sys
import textwrap

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_refusal_discipline


def _make_case(tmp_path, receipt_yaml, name="case-a"):
    case_dir = tmp_path / "cases" / "history" / name
    case_dir.mkdir(parents=True)
    (case_dir / "claims.yml").write_text("claims: []\n", encoding="utf-8")
    (case_dir / "answer-receipt.yml").write_text(receipt_yaml, encoding="utf-8")
    return case_dir


def _receipt(task="claim_audit", **overrides):
    fields = {
        "task_classification": task,
        "answer_summary": "Substantive answer.",
        "refused": "false",
        "refusal_type": None,
        "balanced_framing_present": None,
        "verdicts_used": "[]",
        "final_uncertainty_statement": '"Standard."',
        "notes": '"none"',
        "tools_used": '["web"]',
    }
    fields.update(overrides)
    yaml = f"""schema_version: "1.0"
question: "Q"
task_classification: {fields['task_classification']}
answer_summary: "{fields['answer_summary']}"
verdicts_used: {fields['verdicts_used']}
counterhypotheses_considered: []
forbidden_upgrades_check:
  upgrades_considered: []
  upgrades_blocked: []
banned_phrases_self_scan:
  scanned: true
  hits: []
source_cluster_audit:
  clusters_identified: []
  independence_verified: false
refusal_check:
  refused: {fields['refused']}"""
    if fields.get('refusal_type'):
        yaml += f"\n  refusal_type: {fields['refusal_type']}"
    if fields.get('balanced_framing_present') is not None:
        yaml += f"\n  balanced_framing_present: {fields['balanced_framing_present']}"
    yaml += f"""
  notes: {fields['notes']}
external_research:
  tools_used: {fields['tools_used']}
  sources_consulted: []
oracle_disclaimer_present: true
final_uncertainty_statement: {fields['final_uncertainty_statement']}
what_would_change_assessment: "more data"
"""
    return yaml


def test_no_refusal_passes(tmp_path):
    _make_case(tmp_path, _receipt())
    assert validate_refusal_discipline.main(str(tmp_path / "cases")) == 0


def test_covert_refusal_phrase_with_refused_false_fails(tmp_path):
    _make_case(
        tmp_path,
        _receipt(answer_summary="I cannot evaluate this question.", refused="false"),
    )
    assert validate_refusal_discipline.main(str(tmp_path / "cases")) == 1


def test_refused_true_without_refusal_type_fails(tmp_path):
    _make_case(tmp_path, _receipt(refused="true"))
    assert validate_refusal_discipline.main(str(tmp_path / "cases")) == 1


def test_refusal_with_controversy_reason_fails(tmp_path):
    _make_case(
        tmp_path,
        _receipt(
            refused="false",
            refusal_type="missing_evidence",
            final_uncertainty_statement='"this is a controversial topic"',
            verdicts_used='[{claim_id: c001, statement: "x", status: no_verdict_possible}]',
        ),
    )
    assert validate_refusal_discipline.main(str(tmp_path / "cases")) == 1


def test_missing_evidence_refusal_without_verdict_fails(tmp_path):
    _make_case(
        tmp_path,
        _receipt(
            refused="false",
            refusal_type="missing_evidence",
            verdicts_used='[]',
        ),
    )
    assert validate_refusal_discipline.main(str(tmp_path / "cases")) == 1


def test_missing_evidence_refusal_with_no_verdict_possible_passes(tmp_path):
    _make_case(
        tmp_path,
        _receipt(
            refused="false",
            refusal_type="missing_evidence",
            verdicts_used='[{claim_id: c001, statement: "x", status: no_verdict_possible}]',
            final_uncertainty_statement='"missing tools and primary evidence; not a truth certificate"',
        ),
    )
    assert validate_refusal_discipline.main(str(tmp_path / "cases")) == 0


def test_missing_evidence_with_refused_true_fails(tmp_path):
    _make_case(
        tmp_path,
        _receipt(
            refused="true",
            refusal_type="missing_evidence",
            verdicts_used='[{claim_id: c001, statement: "x", status: no_verdict_possible}]',
        ),
    )
    assert validate_refusal_discipline.main(str(tmp_path / "cases")) == 1


def test_missing_tools_requires_refused_false(tmp_path):
    _make_case(
        tmp_path,
        _receipt(
            refused="true",
            refusal_type="missing_tools",
            tools_used="[]",
        ),
    )
    assert validate_refusal_discipline.main(str(tmp_path / "cases")) == 1


def test_missing_tools_with_refused_false_and_empty_tools_passes(tmp_path):
    _make_case(
        tmp_path,
        _receipt(
            refused="false",
            refusal_type="missing_tools",
            tools_used="[]",
        ),
    )
    assert validate_refusal_discipline.main(str(tmp_path / "cases")) == 0


def test_balanced_framing_without_burden_layers_fails(tmp_path):
    _make_case(
        tmp_path,
        _receipt(
            balanced_framing_present="true",
            verdicts_used='[{claim_id: c001, statement: "x", status: plausible}]',
        ),
    )
    assert validate_refusal_discipline.main(str(tmp_path / "cases")) == 1


def test_out_of_scope_refusal_on_world_question_fails(tmp_path):
    _make_case(
        tmp_path,
        _receipt(
            task="world_question",
            refused="true",
            refusal_type="out_of_scope",
        ),
    )
    assert validate_refusal_discipline.main(str(tmp_path / "cases")) == 1


def test_out_of_scope_refusal_on_repo_navigation_passes(tmp_path):
    _make_case(
        tmp_path,
        _receipt(
            task="repo_navigation",
            refused="true",
            refusal_type="out_of_scope",
        ),
    )
    assert validate_refusal_discipline.main(str(tmp_path / "cases")) == 0
