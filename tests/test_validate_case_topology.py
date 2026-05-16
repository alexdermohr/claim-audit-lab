"""Tests for scripts/validate_case_topology.py."""

from datetime import date, timedelta
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import case_compat
import validate_case_topology

FIXTURE_ROOT = pathlib.Path(__file__).parent / "fixtures" / "case_topology"


def test_claims_without_evidence_relations_fails():
    errors = validate_case_topology.validate_case(FIXTURE_ROOT / "invalid" / "claims_without_evidence_relations")
    assert any("evidence-relations.yml required because claims.yml exists" in e for e in errors), errors


def test_evidence_pack_without_claims_fails():
    errors = validate_case_topology.validate_case(FIXTURE_ROOT / "invalid" / "evidence_pack_without_claims")
    assert any("claims.yml required because evidence-pack.yml exists" in e for e in errors), errors


def test_assessment_without_relations_fails():
    errors = validate_case_topology.validate_case(FIXTURE_ROOT / "invalid" / "assessment_without_relations")
    assert any("evidence-relations.yml required because assessment.md exists" in e for e in errors), errors


def test_hypotheses_without_support_ledger_fails():
    errors = validate_case_topology.validate_case(FIXTURE_ROOT / "invalid" / "hypotheses_without_support_ledger")
    assert any("hypothesis-support-ledger.yml required because hypotheses.yml exists" in e for e in errors), errors


def test_redteam_without_assessment_fails():
    errors = validate_case_topology.validate_case(FIXTURE_ROOT / "invalid" / "redteam_without_assessment")
    assert any("assessment.md required because redteam.yml or redteam.md exists" in e for e in errors), errors


def test_minimal_valid_case_passes():
    errors = validate_case_topology.validate_case(FIXTURE_ROOT / "valid" / "minimal_valid_case")
    assert errors == []


def test_cli_discovers_case_roots_from_any_case_artifact(capsys):
    exit_code = validate_case_topology.main(str(FIXTURE_ROOT / "invalid" / "redteam_without_assessment"))
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL" in captured.out
    assert "assessment.md required because redteam.yml or redteam.md exists" in captured.out


def write_legacy_marker(path, allowlist=True, today=None, **overrides):
    if allowlist:
        root = path.parent if path.name != "cases" else path
        while root != root.parent and root.name != "cases":
            root = root.parent
        if root.name != "cases":
            root = path / "cases"
            path = root / "allowed-case"
            path.mkdir(parents=True, exist_ok=True)
        rel = path.relative_to(root).as_posix()
        (root / "_legacy-allowlist.yml").write_text(f'schema_version: "1.0"\nallowed_legacy_cases: ["{rel}"]\n', encoding="utf-8")
    today = today or date.today()
    payload = {
        "legacy_case": True,
        "created_at": today.isoformat(),
        "expires_on": (today + timedelta(days=60)).isoformat(),
        "migration_target": "Fixture migration target.",
        "reason": "Fixture legacy reason.",
    }
    payload.update(overrides)
    lines = []
    for key, value in payload.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        else:
            rendered = f'"{value}"'
        lines.append(f"{key}: {rendered}")
    (path / "legacy-case.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_legacy_case_requires_reason(tmp_path):
    case_dir = tmp_path / "cases" / "allowed-case"
    case_dir.mkdir(parents=True)
    write_legacy_marker(case_dir, today=date(2026, 5, 15), reason="")
    assert "reason" in case_compat.legacy_case_error(case_dir, today=date(2026, 5, 15))


def test_legacy_case_requires_created_at(tmp_path):
    case_dir = tmp_path / "cases" / "allowed-case"
    case_dir.mkdir(parents=True)
    write_legacy_marker(case_dir, today=date(2026, 5, 15))
    text = (case_dir / "legacy-case.yml").read_text(encoding="utf-8")
    (case_dir / "legacy-case.yml").write_text("\n".join(line for line in text.splitlines() if not line.startswith("created_at:")) + "\n", encoding="utf-8")
    assert "created_at" in case_compat.legacy_case_error(case_dir, today=date(2026, 5, 15))


def test_legacy_case_rejects_far_future_expiry(tmp_path):
    case_dir = tmp_path / "cases" / "allowed-case"
    case_dir.mkdir(parents=True)
    write_legacy_marker(case_dir, today=date(2026, 5, 15), expires_on="2026-07-15")
    assert "within 60 days" in case_compat.legacy_case_error(case_dir, today=date(2026, 5, 15))


def test_legacy_case_rejects_expired_marker(tmp_path):
    case_dir = tmp_path / "cases" / "allowed-case"
    case_dir.mkdir(parents=True)
    write_legacy_marker(case_dir, today=date(2026, 5, 15), expires_on="2026-05-14")
    assert "expired" in case_compat.legacy_case_error(case_dir, today=date(2026, 5, 15))


def test_legacy_case_is_visible_in_cli_output(tmp_path, capsys):
    case_dir = tmp_path / "cases" / "allowed-case"
    case_dir.mkdir(parents=True)
    write_legacy_marker(case_dir)
    (case_dir / "claims.yml").write_text("schema_version: '1.0'\nclaims: []\n", encoding="utf-8")
    exit_code = validate_case_topology.main(str(tmp_path / "cases"))
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "LEGACY" in captured.out
    assert f"temporarily exempt until {(date.today() + timedelta(days=60)).isoformat()}" in captured.out


def test_unknown_case_with_legacy_marker_fails(tmp_path):
    case_dir = tmp_path / "cases" / "unknown-case"
    case_dir.mkdir(parents=True)
    (tmp_path / "cases" / "_legacy-allowlist.yml").write_text('schema_version: "1.0"\nallowed_legacy_cases: []\n', encoding="utf-8")
    write_legacy_marker(case_dir, allowlist=False)
    errors = validate_case_topology.validate_case(case_dir)
    assert any("not allowed" in e for e in errors), errors


def test_allowlisted_legacy_case_passes_topology_exemption(tmp_path):
    case_dir = tmp_path / "cases" / "allowed-case"
    case_dir.mkdir(parents=True)
    write_legacy_marker(case_dir)
    (case_dir / "claims.yml").write_text("schema_version: '1.0'\nclaims: []\n", encoding="utf-8")
    errors = validate_case_topology.validate_case(case_dir)
    assert errors == []


def test_assessment_with_unallowlisted_legacy_marker_does_not_pass_silently(tmp_path):
    case_dir = tmp_path / "cases" / "unknown-case"
    case_dir.mkdir(parents=True)
    (tmp_path / "cases" / "_legacy-allowlist.yml").write_text('schema_version: "1.0"\nallowed_legacy_cases: []\n', encoding="utf-8")
    write_legacy_marker(case_dir, allowlist=False)
    (case_dir / "assessment.md").write_text("# Assessment\n", encoding="utf-8")
    errors = validate_case_topology.validate_case(case_dir)
    assert any("not allowed" in e for e in errors), errors
