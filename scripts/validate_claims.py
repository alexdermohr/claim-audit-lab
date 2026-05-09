#!/usr/bin/env python3
"""Validate claims.yml files in all cases against claim.v1.schema.json."""

import sys
import json
import pathlib
import yaml
import jsonschema

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "claim.v1.schema.json"

CAUSAL_CLAIM_MIN_COUNTERCLAIMS = 2
STRONG_STATUSES = {"established", "strongly_supported"}


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def validate_claim(claim: dict, schema: dict) -> list[str]:
    """Return list of error messages for a single claim dict."""
    errors = []

    validator = jsonschema.Draft7Validator(schema)
    for error in validator.iter_errors(claim):
        errors.append(f"  Schema error at {list(error.absolute_path)}: {error.message}")

    if errors:
        return errors

    claim_type = claim.get("claim_type", "")
    requires = claim.get("requires", [])
    counterclaims = claim.get("counterclaims", [])
    source_refs = claim.get("source_refs", [])
    evidence_refs = claim.get("evidence_refs", [])
    status = claim.get("status", "")

    if claim_type == "causal_claim" and len(counterclaims) < CAUSAL_CLAIM_MIN_COUNTERCLAIMS:
        errors.append(
            f"  causal_claim '{claim['claim_id']}' requires at least {CAUSAL_CLAIM_MIN_COUNTERCLAIMS} `counterclaims`. "
            f"Found counterclaims={counterclaims}"
        )

    if claim_type == "motive_claim":
        for req in ["capability", "interest"]:
            if req not in requires:
                errors.append(
                    f"  motive_claim '{claim['claim_id']}' missing '{req}' in `requires`."
                )

    if claim_type == "statistical_claim":
        if "method" not in requires and "dataset" not in requires:
            errors.append(
                f"  statistical_claim '{claim['claim_id']}' must have 'method' or 'dataset' in `requires`."
            )

    if claim_type == "legal_claim" and "primary_legal_source" not in requires:
        errors.append(
            f"  legal_claim '{claim['claim_id']}' must have 'primary_legal_source' in `requires`."
        )

    if status in STRONG_STATUSES and not source_refs:
        errors.append(
            f"  Claim '{claim['claim_id']}' has status '{status}' but no `source_refs`."
        )

    if status in STRONG_STATUSES and not evidence_refs:
        errors.append(
            f"  Claim '{claim['claim_id']}' has status '{status}' but no `evidence_refs`."
        )

    return errors


def validate_file(claims_file: pathlib.Path, schema: dict) -> int:
    """Validate a single claims.yml file. Returns number of errors."""
    try:
        with open(claims_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"FAIL {claims_file}: Could not parse YAML: {e}")
        return 1

    if not isinstance(data, dict) or "claims" not in data:
        print(f"FAIL {claims_file}: Missing top-level 'claims' key.")
        return 1

    total_errors = 0
    for claim in data["claims"]:
        errs = validate_claim(claim, schema)
        if errs:
            print(f"FAIL {claims_file} [{claim.get('claim_id', '?')}]:")
            for e in errs:
                print(e)
            total_errors += len(errs)

    if total_errors == 0:
        print(f"OK   {claims_file}")

    return total_errors


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    schema = load_schema()

    files = sorted(root.rglob("claims.yml"))

    if not files:
        print(f"No claims.yml files found under {root}")
        return 0

    total_errors = 0
    for f in files:
        if "_template" in f.parts:
            continue
        total_errors += validate_file(f, schema)

    if total_errors:
        print(f"\n{total_errors} error(s) found.")
        return 1

    print("\nAll claims valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
