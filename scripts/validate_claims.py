#!/usr/bin/env python3
"""Validate claims.yml files in all cases against claim.v1.schema.json."""

import sys
import json
import pathlib
import yaml
from jsonschema_compat import jsonschema

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "claim.v1.schema.json"

CAUSAL_CLAIM_MIN_COUNTERCLAIMS = 2
STRONG_STATUSES = {"established", "strongly_supported"}
ABSENCE_SCOPE_MARKERS = {
    "evidence-pack",
    "evidence pack",
    "quelle",
    "source",
    "dataset",
    "quellenset",
    "source set",
    "auditierte",
    "audited",
    "vorliegenden",
    "vorliegend",
    "within",
    "in the reviewed",
    "im untersuchten",
    "in untersuchtem",
}
CO_CAUSATION_TERMS = (
    "mitverursachte",
    "mitverursacht",
    "contributed",
    "contributes",
    "co-cause",
    "co-causal",
    "partial cause",
    "partly caused",
)


def load_schema():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def has_absence_scope(claim: dict) -> bool:
    """Return whether an absence_claim declares a bounded search scope."""
    explicit_scope = claim.get("absence_scope") or claim.get("scope")
    if isinstance(explicit_scope, str) and explicit_scope.strip():
        return True
    if isinstance(explicit_scope, list) and any(isinstance(item, str) and item.strip() for item in explicit_scope):
        return True

    text_parts = [
        claim.get("statement", ""),
        claim.get("notes", ""),
        " ".join(item for item in claim.get("requires", []) if isinstance(item, str)),
    ]
    text = " ".join(text_parts).lower()
    return any(marker in text for marker in ABSENCE_SCOPE_MARKERS)


def has_co_causation_language(claim: dict) -> bool:
    text = " ".join(
        str(claim.get(key, "")) for key in ("statement", "notes")
    ).lower()
    return any(term in text for term in CO_CAUSATION_TERMS)


def validate_claim(claim: dict, schema: dict) -> list[str]:
    """Return list of error messages for a single claim dict."""
    errors = []

    validator = jsonschema.Draft7Validator(schema)
    for error in validator.iter_errors(claim):
        errors.append(f"  Schema error at {list(error.absolute_path)}: {error.message}")

    if errors:
        return errors

    claim_type = claim.get("claim_type", "")
    claim_kind = claim.get("claim_kind", claim_type)
    burden_profile = claim.get("burden_profile")
    requires = claim.get("requires", [])
    counterclaims = claim.get("counterclaims", [])
    source_refs = claim.get("source_refs", [])
    evidence_refs = claim.get("evidence_refs", [])
    status = claim.get("status", "")
    forbidden_upgrades = claim.get("forbidden_upgrades", [])

    if claim_kind == "reported_claim" and burden_profile != "source_report":
        errors.append(
            f"  reported_claim '{claim['claim_id']}' must set burden_profile='source_report' so source-content closure is not treated as world-claim closure."
        )

    if claim_kind == "absence_claim":
        if not has_absence_scope(claim):
            errors.append(
                f"  absence_claim '{claim['claim_id']}' must declare a bounded scope (for example: within this evidence-pack, in source X, or in dataset Y)."
            )
        if "absence_of_evidence_to_falsehood" not in forbidden_upgrades:
            errors.append(
                f"  absence_claim '{claim['claim_id']}' must include forbidden_upgrades: absence_of_evidence_to_falsehood."
            )

    if has_co_causation_language(claim) and status == "contradicted":
        direct_basis = claim.get("direct_incompatibility_basis")
        if not isinstance(direct_basis, str) or not direct_basis.strip():
            errors.append(
                f"  co-causation claim '{claim['claim_id']}' cannot be status='contradicted' from a stronger alternative explanation alone; set non-empty direct_incompatibility_basis."
            )

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
    if not isinstance(data.get("claims"), list):
        print(f"FAIL {claims_file}: Top-level 'claims' must be an array.")
        return 1

    total_errors = 0
    for claim in data["claims"]:
        if not isinstance(claim, dict):
            print(f"FAIL {claims_file} [?]: claim item must be an object.")
            total_errors += 1
            continue
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
