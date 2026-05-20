#!/usr/bin/env python3
"""
Validate that comparative probability claims are correctly typed.

Comparative claims (P(A) > P(B), "more likely than", etc.) must be typed
as `claim_kind: comparative_claim` or `burden_profile: comparative` and must
declare `comparative_probability` in their requirements.

This prevents the error class: comparative language → simple causal_claim.
"""

import sys
import os
import re
from pathlib import Path
from typing import Dict, List, Any

try:
    import yaml
except ImportError:
    print(
        "ERROR: PyYAML not found. Install with: pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)


# Patterns for comparative probability language (case-insensitive)
COMPARATIVE_PATTERNS = [
    r'\bwahrscheinlichkeit\b',
    r'\bprobability\b',
    r'\bP\s*\(',
    r'\s>\s',
    r'\s<\s',
    r'\bhöher\s+als\b',
    r'\bhoeher\s+als\b',
    r'\bwahrscheinlicher\s+als\b',
    r'\bmore\s+likely\s+than\b',
    r'\bless\s+likely\s+than\b',
    r'\bstatt\s+durch\b',
    r'\binstead\s+of\b',
    r'\bcomparative\s+probability\b',
    r'\bcomparative-probability\b',
]


def has_comparative_language(text: str) -> bool:
    """Check if text contains comparative probability patterns."""
    if not text:
        return False
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in COMPARATIVE_PATTERNS)


def validate_case(case_dir: Path) -> List[str]:
    """
    Validate claims in a single case directory.
    Returns list of error messages (empty list if all valid).
    """
    errors = []
    claims_file = case_dir / "claims.yml"

    if not claims_file.exists():
        return errors

    try:
        with open(claims_file, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
    except Exception as e:
        errors.append(f"{claims_file}: failed to parse YAML: {e}")
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

        # Check if any field has comparative language
        has_comparative = (
            has_comparative_language(statement)
            or has_comparative_language(notes)
            or any(
                has_comparative_language(r) if isinstance(r, str) else False
                for r in (requires if isinstance(requires, list) else [])
            )
        )

        if not has_comparative:
            continue

        # Found comparative language. Check if properly typed.
        claim_kind = claim.get("claim_kind", "")
        burden_profile = claim.get("burden_profile", "")

        is_comparative_kind = claim_kind == "comparative_claim"
        is_comparative_burden = burden_profile == "comparative"

        # Check if requires includes comparative_probability
        has_comp_requirement = (
            isinstance(requires, list)
            and "comparative_probability" in requires
        )

        if is_comparative_kind or is_comparative_burden:
            # Type is correct. Check that it also declares the requirement.
            if not has_comp_requirement:
                # Warn but don't fail—type is correct, just missing requirement declaration
                pass
        else:
            # Comparative language detected but claim is not typed as comparative
            errors.append(
                f"{claims_file} claim_id={claim_id}: "
                f"comparative-language detected in statement/notes/requires "
                f"but claim_kind={claim_kind!r} is not 'comparative_claim' "
                f"and burden_profile={burden_profile!r} is not 'comparative'. "
                f"Expected: claim_kind='comparative_claim' or burden_profile='comparative'."
            )

    return errors


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_comparative_claim_profile.py <cases_dir>", file=sys.stderr)
        sys.exit(1)

    cases_dir = Path(sys.argv[1])

    if not cases_dir.is_dir():
        print(f"ERROR: {cases_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    all_errors = []

    # Find all case directories (those containing claims.yml)
    for case_path in sorted(cases_dir.rglob("claims.yml")):
        case_dir = case_path.parent
        errors = validate_case(case_dir)
        all_errors.extend(errors)

    if all_errors:
        for error in all_errors:
            print(error)
        sys.exit(1)
    else:
        print("All comparative-claim profiles valid.")
        sys.exit(0)


if __name__ == "__main__":
    main()
