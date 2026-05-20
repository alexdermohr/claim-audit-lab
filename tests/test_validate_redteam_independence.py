"""Tests for scripts/validate_redteam_independence.py"""

import pathlib
import sys
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_redteam_independence


def _write_case(tmp_path, redteam_data: dict, case_id: str = "test-case") -> pathlib.Path:
    case_dir = tmp_path / "cases" / "sandbox" / case_id
    case_dir.mkdir(parents=True)
    (case_dir / "redteam.yml").write_text(
        yaml.dump(redteam_data, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )
    # Minimal marker file for case discovery
    (case_dir / "evidence-relations.yml").write_text(
        "schema_version: '1.0'\nrelations: []\n", encoding="utf-8"
    )
    return case_dir


def _base_redteam(**overrides) -> dict:
    base = {
        "schema_version": "1.0",
        "review_id": "rt001",
        "assessment_ref": "cases/sandbox/test-case/assessment.md",
        "reviewer": "lab-maintainer",
        "reviewed_at": "2026-05-20",
        "redteam_questions": ["What assumption does this assessment carry unspoken?"],
        "findings": [],
        "verdict": {"status": "pending", "reason": "Draft."},
    }
    base.update(overrides)
    return base


# ---------- Fail tests ----------


def test_non_independent_reviewer_with_pass_verdict_fails(tmp_path):
    """reviewer: assistant-redteam + verdict.status: passed_with_notes → fail."""
    data = _base_redteam(reviewer="assistant-redteam", verdict={"status": "passed_with_notes"})
    _write_case(tmp_path, data)
    result = validate_redteam_independence.main(str(tmp_path / "cases"))
    assert result == 1, "Expected failure: non-independent reviewer with pass verdict"


def test_self_review_independence_with_pass_verdict_fails(tmp_path):
    """reviewer_independence.status: self_review + verdict.status: passed → fail."""
    data = _base_redteam(
        reviewer="lab-maintainer",
        reviewer_independence={"status": "self_review"},
        verdict={"status": "passed"},
    )
    _write_case(tmp_path, data, case_id="case-self-review")
    result = validate_redteam_independence.main(str(tmp_path / "cases"))
    assert result == 1, "Expected failure: self_review independence with pass verdict"


def test_unresolved_high_finding_blocks_pass_verdict(tmp_path):
    """High finding without resolved status + passed_with_notes → fail."""
    data = _base_redteam(
        reviewer_independence={"status": "independent"},
        findings=[
            {
                "id": "f001",
                "severity": "high",
                "issue": "Critical issue not resolved.",
            }
        ],
        verdict={"status": "passed_with_notes"},
    )
    _write_case(tmp_path, data)
    result = validate_redteam_independence.main(str(tmp_path / "cases"))
    assert result == 1, "Expected failure: unresolved high finding with pass verdict"


def test_high_finding_status_open_blocks_pass(tmp_path):
    """High finding with status: open + passed → fail."""
    data = _base_redteam(
        reviewer_independence={"status": "independent"},
        findings=[
            {
                "id": "f001",
                "severity": "high",
                "issue": "Open high issue.",
                "status": "open",
            }
        ],
        verdict={"status": "passed"},
    )
    _write_case(tmp_path, data, case_id="case-open-high")
    result = validate_redteam_independence.main(str(tmp_path / "cases"))
    assert result == 1, "Expected failure: high finding status=open with pass"


def test_error_message_includes_reviewer_and_verdict(tmp_path):
    """Error message must name the reviewer pattern and the verdict status."""
    from io import StringIO
    import contextlib

    data = _base_redteam(reviewer="claude-agent", verdict={"status": "passed_with_notes"})
    _write_case(tmp_path, data)

    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        result = validate_redteam_independence.main(str(tmp_path / "cases"))

    assert result == 1
    output = buf.getvalue()
    assert "claude-agent" in output
    assert "passed_with_notes" in output


def test_empty_reviewer_with_pass_verdict_fails(tmp_path):
    """reviewer: '' + verdict.status: passed_with_notes must fail without independence metadata."""
    from io import StringIO
    import contextlib

    data = _base_redteam(reviewer="", verdict={"status": "passed_with_notes"})
    _write_case(tmp_path, data, case_id="case-empty-reviewer")

    buf = StringIO()
    with contextlib.redirect_stdout(buf):
        result = validate_redteam_independence.main(str(tmp_path / "cases"))

    assert result == 1
    output = buf.getvalue()
    assert "reviewer" in output or "<empty>" in output
    assert "passed_with_notes" in output


def test_non_independent_reviewer_cannot_self_declare_independent(tmp_path):
    """assistant reviewer with reviewer_independence=independent cannot pass."""
    data = _base_redteam(
        reviewer="assistant-redteam",
        reviewer_independence={"status": "independent"},
        verdict={"status": "passed"},
    )
    _write_case(tmp_path, data, case_id="case-self-declared-independent")
    result = validate_redteam_independence.main(str(tmp_path / "cases"))
    assert result == 1, "Expected failure: non-independent reviewer cannot self-declare independent"


def test_pass_verdict_without_reviewer_independence_block_fails(tmp_path):
    """reviewer='lab-maintainer' + no reviewer_independence block + verdict='passed' must fail."""
    data = _base_redteam(
        reviewer="lab-maintainer",
        verdict={"status": "passed"},
    )
    _write_case(tmp_path, data, case_id="case-missing-independence-block")
    result = validate_redteam_independence.main(str(tmp_path / "cases"))
    assert result == 1, "Expected failure: pass verdict without reviewer_independence block"


# ---------- Pass tests ----------


def test_external_reviewer_with_explicit_independent_status_passes(tmp_path):
    """reviewer='external-reviewer' + reviewer_independence.status='independent' + passed → pass."""
    data = _base_redteam(
        reviewer="external-reviewer",
        reviewer_independence={"status": "independent"},
        verdict={"status": "passed"},
    )
    _write_case(tmp_path, data, case_id="case-external-independent")
    result = validate_redteam_independence.main(str(tmp_path / "cases"))
    assert result == 0, "Expected pass: explicit independent block with non-bot reviewer name"


def test_non_independent_reviewer_with_self_review_only_passes(tmp_path):
    """reviewer: assistant-redteam + verdict.status: self_review_only → pass."""
    data = _base_redteam(
        reviewer="assistant-redteam",
        reviewer_independence={"status": "self_review"},
        verdict={"status": "self_review_only"},
    )
    _write_case(tmp_path, data)
    result = validate_redteam_independence.main(str(tmp_path / "cases"))
    assert result == 0, "Expected pass: self_review_only verdict for non-independent reviewer"


def test_resolved_high_finding_with_independent_reviewer_passes(tmp_path):
    """High finding with status: resolved + resolution_refs + independent → pass."""
    data = _base_redteam(
        reviewer_independence={"status": "independent"},
        findings=[
            {
                "id": "f001",
                "severity": "high",
                "issue": "Resolved issue.",
                "status": "resolved",
                "resolution_refs": ["assessment.md#fix"],
            }
        ],
        verdict={"status": "passed_with_notes"},
    )
    _write_case(tmp_path, data)
    result = validate_redteam_independence.main(str(tmp_path / "cases"))
    assert result == 0, "Expected pass: high finding resolved with independent reviewer"


def test_independent_reviewer_no_high_findings_passes(tmp_path):
    """reviewer_independence.status: independent + verdict: passed + no high findings → pass."""
    data = _base_redteam(
        reviewer_independence={"status": "independent"},
        findings=[
            {"id": "f001", "severity": "low", "issue": "Minor note."},
            {"id": "f002", "severity": "medium", "issue": "Medium note."},
        ],
        verdict={"status": "passed"},
    )
    _write_case(tmp_path, data, case_id="case-independent")
    result = validate_redteam_independence.main(str(tmp_path / "cases"))
    assert result == 0, "Expected pass: independent reviewer, no high findings, passed"


def test_pending_verdict_skips_independence_check(tmp_path):
    """A pending verdict should not be flagged regardless of reviewer."""
    data = _base_redteam(
        reviewer="assistant-redteam",
        verdict={"status": "pending"},
    )
    _write_case(tmp_path, data)
    result = validate_redteam_independence.main(str(tmp_path / "cases"))
    assert result == 0, "Expected pass: pending verdict is always allowed"
