"""Tests for scripts/validate_lifecycle.py"""

import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_lifecycle

SCHEMAS_DIR = pathlib.Path(__file__).parent.parent / "schemas"


def load_lifecycle_schema() -> dict:
    with open(SCHEMAS_DIR / "lifecycle.v1.schema.json", encoding="utf-8") as f:
        return json.load(f)


def load_redteam_schema() -> dict:
    with open(SCHEMAS_DIR / "redteam-review.v1.schema.json", encoding="utf-8") as f:
        return json.load(f)


def write_yaml(path: pathlib.Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False)


def base_lifecycle(**overrides) -> dict:
    payload = {
        "schema_version": "1.0",
        "assessment_id": "a001",
        "case_ref": "cases/sandbox/test-case",
        "status": "draft",
        "created_at": "2026-05-09",
        "last_reviewed_at": "2026-05-09",
        "review_after": "2026-08-09",
        "redteam_ref": "redteam.yml",
        "reopen_triggers": ["new_primary_source"],
        "history": [{"date": "2026-05-09", "status": "draft", "note": "Case opened."}],
    }
    payload.update(overrides)
    return payload


def base_redteam(status: str = "pending") -> dict:
    return {
        "schema_version": "1.0",
        "review_id": "rt001",
        "assessment_ref": "cases/sandbox/test-case/assessment.md",
        "reviewer": "qa",
        "reviewed_at": "2026-05-09",
        "redteam_questions": ["What assumption is unspoken?"],
        "findings": [],
        "verdict": {"status": status, "reason": "fixture"},
    }


def run_validate(tmp_path: pathlib.Path, lifecycle_payload: dict, redteam_payload: dict | None) -> list[str]:
    case_dir = tmp_path / "case"
    lifecycle_path = case_dir / "lifecycle.yml"
    write_yaml(lifecycle_path, lifecycle_payload)

    if redteam_payload is not None:
        redteam_path = case_dir / lifecycle_payload.get("redteam_ref", "redteam.yml")
        write_yaml(redteam_path, redteam_payload)

    return validate_lifecycle.validate_lifecycle_file(
        lifecycle_path,
        load_lifecycle_schema(),
        load_redteam_schema(),
    )


def test_invalid_lifecycle_status_fails(tmp_path):
    errors = run_validate(tmp_path, base_lifecycle(status="invalid_status"), base_redteam())
    assert any("status" in e for e in errors)


def test_malformed_assessment_id_fails(tmp_path):
    errors = run_validate(tmp_path, base_lifecycle(assessment_id="bad"), base_redteam())
    assert any("assessment_id" in e for e in errors)


def test_invalid_review_after_date_fails(tmp_path):
    errors = run_validate(tmp_path, base_lifecycle(review_after="2026-99-99"), base_redteam())
    assert any("review_after" in e for e in errors)


def test_final_without_redteam_fails(tmp_path):
    lifecycle = base_lifecycle(status="final_under_uncertainty")
    errors = run_validate(tmp_path, lifecycle, None)
    assert any("requires a red-team file" in e for e in errors)


def test_final_with_blocked_redteam_fails(tmp_path):
    lifecycle = base_lifecycle(status="final_under_uncertainty")
    errors = run_validate(tmp_path, lifecycle, base_redteam(status="blocked"))
    assert any("requires red-team verdict" in e for e in errors)


def test_final_with_passed_redteam_passes(tmp_path):
    lifecycle = base_lifecycle(status="final_under_uncertainty")
    errors = run_validate(tmp_path, lifecycle, base_redteam(status="passed"))
    assert errors == []


def test_redteam_ref_is_honored(tmp_path):
    lifecycle = base_lifecycle(redteam_ref="custom-redteam.yml")
    errors = run_validate(tmp_path, lifecycle, base_redteam(status="pending"))
    assert errors == []
