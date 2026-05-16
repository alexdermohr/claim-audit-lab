"""Shared compatibility helpers for legacy case migration windows."""

from __future__ import annotations

from datetime import date, timedelta
import pathlib
import yaml

MAX_LEGACY_DAYS = 60
ALLOWLIST_FILENAME = "_legacy-allowlist.yml"


def safe_load_yaml(path: pathlib.Path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except Exception as exc:
        return None, str(exc)


def find_cases_root(case_dir: pathlib.Path) -> pathlib.Path | None:
    for candidate in (case_dir, *case_dir.parents):
        if candidate.name == "cases":
            return candidate
    return None


def legacy_allowlist_error(case_dir: pathlib.Path) -> str | None:
    cases_root = find_cases_root(case_dir)
    if cases_root is None:
        return None
    allowlist_path = cases_root / ALLOWLIST_FILENAME
    if not allowlist_path.exists():
        return f"legacy-case.yml requires {ALLOWLIST_FILENAME}."
    data, err = safe_load_yaml(allowlist_path)
    if err:
        return f"Could not parse {ALLOWLIST_FILENAME}: {err}"
    if not isinstance(data, dict):
        return f"{ALLOWLIST_FILENAME} must contain a YAML object."
    allowed = data.get("allowed_legacy_cases", [])
    if not isinstance(allowed, list):
        return f"{ALLOWLIST_FILENAME} allowed_legacy_cases must be an array."
    rel = case_dir.relative_to(cases_root).as_posix()
    full_rel = f"cases/{rel}"
    if rel not in allowed and full_rel not in allowed:
        return f"legacy-case.yml not allowed for {case_dir}; add it to {ALLOWLIST_FILENAME}."
    return None


def _parse_iso_date(value, field: str) -> tuple[date | None, str | None]:
    if not isinstance(value, str) or not value.strip():
        return None, f"legacy-case.yml must set non-empty {field}."
    try:
        return date.fromisoformat(value), None
    except ValueError:
        return None, f"legacy-case.yml {field} must be an ISO date (YYYY-MM-DD)."


def legacy_case_error(case_dir: pathlib.Path, today: date | None = None) -> str | None:
    legacy_path = case_dir / "legacy-case.yml"
    if not legacy_path.exists():
        return None

    allowlist_error = legacy_allowlist_error(case_dir)
    if allowlist_error:
        return allowlist_error

    data, err = safe_load_yaml(legacy_path)
    if err:
        return f"Could not parse legacy-case.yml: {err}"
    if not isinstance(data, dict):
        return "legacy-case.yml must contain a YAML object."
    if data.get("legacy_case") is not True:
        return "legacy-case.yml must set legacy_case: true."

    for field in ("reason", "migration_target"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            return f"legacy-case.yml must set non-empty {field}."

    today = today or date.today()
    created_at, err = _parse_iso_date(data.get("created_at"), "created_at")
    if err:
        return err
    expires_on, err = _parse_iso_date(data.get("expires_on"), "expires_on")
    if err:
        return err

    if created_at > today:
        return "legacy-case.yml created_at must not be in the future."
    if expires_on < today:
        return "legacy-case.yml expires_on is expired."
    max_expires_on = today + timedelta(days=MAX_LEGACY_DAYS)
    if expires_on > max_expires_on:
        return f"legacy-case.yml expires_on must be within {MAX_LEGACY_DAYS} days."
    return None


def is_legacy_case(case_dir: pathlib.Path, today: date | None = None) -> bool:
    return (case_dir / "legacy-case.yml").exists() and legacy_case_error(case_dir, today=today) is None


def legacy_case_until(case_dir: pathlib.Path) -> str:
    data, _ = safe_load_yaml(case_dir / "legacy-case.yml")
    if isinstance(data, dict):
        return str(data.get("expires_on", "unknown"))
    return "unknown"
