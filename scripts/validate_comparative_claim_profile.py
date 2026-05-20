#!/usr/bin/env python3
"""
Validate that comparative probability claims are correctly typed.

Comparative claims (P(A) > P(B), "more likely than", etc.) must be typed
as `claim_kind: comparative_claim` or `burden_profile: comparative` and must
declare `comparative_probability` in their requirements (unless burden_profile
is already set to `comparative`, which serves as the declaration).

This prevents the error class: comparative language → simple causal_claim.
"""

import re
import sys
from pathlib import Path
from typing import List

try:
    import yaml
except ImportError:
    print(
        "ERROR: PyYAML not found. Install with: pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)


COMPARATIVE_PATTERNS = [
    r"\bp\s*\([^)]*\)\s*[<>]\s*p\s*\([^)]*\)",
    r"\bwahrscheinlicher\s+als\b",
    r"\bhöher\s+als\b",
    r"\bhoeher\s+als\b",
    r"\bmore\s+likely\s+than\b",
    r"\bless\s+likely\s+than\b",
    r"\bhigher\s+than\b",
    r"\binstead\s+of\b",
    r"\brather\s+than\b",
    r"\bstatt\s+durch\b",
    r"\bgegenüber\b",
    r"\bcompared\s+to\b",
]


def has_comparative_language(text: str) -> bool:
    """Check if text contains explicit comparative probability patterns."""
    if not text:
        return False
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in COMPARATIVE_PATTERNS)


def discover_case_dirs(root: Path) -> List[Path]:
    """Discover case directories containing claims.yml, skipping _template."""
    return sorted({
        marker.parent for marker in root.rglob("claims.yml")
        if "_template" not in marker.parts
    })


def validate_case(case_dir: Path) -> List[str]:
    """Validate claims in a single case directory."""
    errors: List[str] = []
    claims_file = case_dir / "claims.yml"

    if not claims_file.exists():
        return errors

    try:
        with open(claims_file, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
    except Exception as exc:
        errors.append(f"{claims_file}: failed to parse YAML: {exc}")
        return errors

    if not content or "claims" not in content:
        return errors

    claims_list = content.get("claims", [])
    if not isinstance(claims_list, list):
        return errors

    for claim in claims_list:
        if not isinstance(claim, dict):
            continue

        claim_id = claim.get("claim_id", "unknown")
        statement = claim.get("statement", "")
        notes = claim.get("notes", "")
        requires = claim.get("requires", [])

        has_comparative = (
            has_comparative_language(statement)
            or has_comparative_language(notes)
            or any(
                has_comparative_language(item) if isinstance(item, str) else False
                for item in (requires if isinstance(requires, list) else [])
            )
        )
        if not has_comparative:
            continue

        claim_kind = claim.get("claim_kind", "")
        burden_profile = claim.get("burden_profile", "")
        is_comparative_kind = claim_kind == "comparative_claim"
        is_comparative_burden = burden_profile == "comparative"
        has_comp_requirement = (
            isinstance(requires, list) and "comparative_probability" in requires
        )

        if not (is_comparative_kind or is_comparative_burden):
            errors.append(
                f"{claims_file} claim_id={claim_id}: "
                f"comparative-language detected in statement/notes/requires "
                f"but claim_kind={claim_kind!r} is not 'comparative_claim' "
                f"and burden_profile={burden_profile!r} is not 'comparative'. "
                f"Expected: claim_kind='comparative_claim' or burden_profile='comparative'."
            )
        elif is_comparative_kind and not is_comparative_burden and not has_comp_requirement:
            errors.append(
                f"{claims_file} claim_id={claim_id}: "
                f"claim_kind='comparative_claim' but 'comparative_probability' is not "
                f"declared in 'requires' and burden_profile is not 'comparative'. "
                f"Add 'comparative_probability' to requires, or set burden_profile='comparative'."
            )

    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: validate_comparative_claim_profile.py <cases_dir>", file=sys.stderr)
        return 1

    cases_dir = Path(sys.argv[1])
    if not cases_dir.is_dir():
        print(f"ERROR: {cases_dir} is not a directory", file=sys.stderr)
        return 1

    case_dirs = discover_case_dirs(cases_dir)
    if not case_dirs:
        print(f"No claims.yml files found under {cases_dir}")
        return 0

    all_errors: List[str] = []
    for case_dir in case_dirs:
        all_errors.extend(validate_case(case_dir))

    if all_errors:
        for error in all_errors:
            print(error)
        return 1

    print("All comparative-claim profiles valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
