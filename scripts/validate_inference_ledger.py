#!/usr/bin/env python3
"""Validate case-local inference-ledger.yml artifacts.

Required when:
  - claim status is established, strongly_supported, or contradicted (unless exempt)
  - claim burden_profile is causal_chain or comparative and status is not
    unresolved or no_verdict_possible (unless exempt)
  - a high-materiality unresolved/partially_resolved defeater targets a strong claim

Exempt from all strong-verdict rules:
  - claim_kind: reported_claim
  - burden_profile: source_report
  - claim_type: meta_claim (case-constitutive scope claims with local sources only)
"""

from collections import Counter
import json
import pathlib
import sys

from jsonschema_compat import jsonschema
import yaml

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "inference-ledger.v1.schema.json"
HIGH_MATERIALITY = 0.75

STRONG_POSITIVE = {"established", "strongly_supported"}
STRONG_NEGATIVE = {"contradicted"}
ALL_STRONG = STRONG_POSITIVE | STRONG_NEGATIVE
UNRESOLVED_DEFEATER_STATUSES = {"unresolved", "partially_resolved"}
# Statuses that trigger inference-ledger requirement for causal_chain/comparative claims.
# Anything except unresolved and no_verdict_possible.
CAUSAL_TRIGGER_STATUSES = {
    "speculative", "weak", "plausible",
    "established", "strongly_supported", "contradicted",
}


def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def safe_load_yaml(path: pathlib.Path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except Exception as exc:
        return None, str(exc)


def load_optional_object(path: pathlib.Path, label: str) -> tuple[dict | None, list[str]]:
    if not path.exists():
        return None, []
    data, err = safe_load_yaml(path)
    if err:
        return None, [f"Could not parse {label}: {err}"]
    if not isinstance(data, dict):
        return None, [f"{label} must contain a YAML object."]
    return data, []


def schema_errors(payload: dict, schema: dict) -> list[str]:
    validator = jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())
    return [
        f"Schema error at {list(error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(payload), key=lambda err: list(err.absolute_path))
    ]


def require_list(data: dict, key: str, label: str, errors: list[str]) -> list:
    if key not in data:
        return []
    value = data.get(key)
    if not isinstance(value, list):
        errors.append(f"{label} '{key}' must be an array.")
        return []
    return value


def is_exempt(claim: dict) -> bool:
    """Return True if the claim is exempt from inference-ledger requirements."""
    if claim.get("claim_kind") == "reported_claim":
        return True
    if claim.get("burden_profile") == "source_report":
        return True
    if claim.get("claim_type") == "meta_claim":
        return True
    return False


def needs_inference_entry(claim: dict) -> bool:
    """Return True if this claim requires an inference-ledger entry."""
    if is_exempt(claim):
        return False
    status = claim.get("status", "")
    if status in ALL_STRONG:
        return True
    burden_profile = claim.get("burden_profile", "")
    if burden_profile in ("causal_chain", "comparative") and status in CAUSAL_TRIGGER_STATUSES:
        return True
    return False


def validate_case(case_dir: pathlib.Path, schema: dict) -> list[str]:
    errors: list[str] = []

    claims_data, load_errors = load_optional_object(case_dir / "claims.yml", "claims.yml")
    errors.extend(load_errors)
    if claims_data is None:
        return errors

    claims = require_list(claims_data, "claims", "claims.yml", errors)
    claim_ids = {
        c.get("claim_id") for c in claims
        if isinstance(c, dict) and isinstance(c.get("claim_id"), str)
    }

    evidence_data, load_errors = load_optional_object(case_dir / "evidence-pack.yml", "evidence-pack.yml")
    errors.extend(load_errors)
    evidence_ids: set[str] | None = None
    if evidence_data is not None:
        evidence = require_list(evidence_data, "evidence", "evidence-pack.yml", errors)
        evidence_ids = {
            e.get("evidence_id") for e in evidence
            if isinstance(e, dict) and isinstance(e.get("evidence_id"), str)
        }

    defeaters_data, load_errors = load_optional_object(case_dir / "model-defeaters.yml", "model-defeaters.yml")
    errors.extend(load_errors)
    defeaters = []
    defeater_ids: set[str] | None = None
    if defeaters_data is not None:
        defeaters = require_list(defeaters_data, "defeaters", "model-defeaters.yml", errors)
        defeater_ids = {
            d.get("defeater_id") for d in defeaters
            if isinstance(d, dict) and isinstance(d.get("defeater_id"), str)
        }

    ledger_path = case_dir / "inference-ledger.yml"
    if not ledger_path.exists():
        for claim in claims:
            if not isinstance(claim, dict):
                continue
            if needs_inference_entry(claim):
                cid = claim.get("claim_id", "?")
                status = claim.get("status", "?")
                errors.append(
                    f"claim '{cid}' (status='{status}') requires an inference-ledger entry, "
                    f"but inference-ledger.yml is absent."
                )
        return errors

    ledger_data, err = safe_load_yaml(ledger_path)
    if err:
        return errors + [f"Could not parse inference-ledger.yml: {err}"]
    if not isinstance(ledger_data, dict):
        return errors + ["inference-ledger.yml must contain a YAML object."]

    errors.extend(schema_errors(ledger_data, schema))
    inferences = require_list(ledger_data, "inferences", "inference-ledger.yml", errors)

    inf_ids = [
        inf.get("inference_id") for inf in inferences
        if isinstance(inf, dict) and isinstance(inf.get("inference_id"), str)
    ]
    for inf_id, count in Counter(inf_ids).items():
        if count > 1:
            errors.append(f"duplicate inference_id '{inf_id}'.")

    all_step_ids: list[str] = []
    claims_covered: set[str] = set()

    for inf in inferences:
        if not isinstance(inf, dict):
            continue
        inf_id = inf.get("inference_id", "?")
        claim_ref = inf.get("claim_ref")

        if isinstance(claim_ref, str) and claim_ref:
            if claim_ref not in claim_ids:
                errors.append(
                    f"inference '{inf_id}' claim_ref '{claim_ref}' not found in claims.yml."
                )
            else:
                claims_covered.add(claim_ref)

        steps = inf.get("inference_steps") or []
        if not isinstance(steps, list):
            continue

        for step in steps:
            if not isinstance(step, dict):
                continue
            step_id = step.get("step_id", "?")
            if isinstance(step_id, str):
                all_step_ids.append(step_id)

            evidence_refs = step.get("premise_evidence_refs") or []
            has_nonempty_evidence_refs = any(
                isinstance(r, str) and r.strip() for r in evidence_refs
            )
            if has_nonempty_evidence_refs and evidence_ids is None:
                errors.append(
                    f"inference-ledger.yml inference '{inf_id}' step '{step_id}': "
                    f"premise_evidence_refs require evidence-pack.yml (missing evidence-pack.yml)."
                )
            elif isinstance(evidence_refs, list) and evidence_ids is not None:
                for ref in evidence_refs:
                    if isinstance(ref, str) and ref not in evidence_ids:
                        errors.append(
                            f"inference '{inf_id}' step '{step_id}' premise_evidence_ref '{ref}' "
                            f"not found in evidence-pack.yml."
                        )

            claim_refs = step.get("premise_claim_refs") or []
            if isinstance(claim_refs, list):
                for ref in claim_refs:
                    if isinstance(ref, str) and ref not in claim_ids:
                        errors.append(
                            f"inference '{inf_id}' step '{step_id}' premise_claim_ref '{ref}' "
                            f"not found in claims.yml."
                        )

            # every step must ground itself in at least one concrete premise
            has_evidence_premise = any(
                isinstance(r, str) and r.strip()
                for r in (step.get("premise_evidence_refs") or [])
            )
            has_claim_premise = any(
                isinstance(r, str) and r.strip()
                for r in (step.get("premise_claim_refs") or [])
            )
            if not has_evidence_premise and not has_claim_premise:
                errors.append(
                    f"inference '{inf_id}' step '{step_id}' must cite at least one "
                    f"premise_evidence_ref or premise_claim_ref."
                )

            # validate addresses_defeater_refs against known defeater_ids
            addr_refs = step.get("addresses_defeater_refs") or []
            if isinstance(addr_refs, list) and defeater_ids is not None:
                for ref in addr_refs:
                    if isinstance(ref, str) and ref not in defeater_ids:
                        errors.append(
                            f"inference '{inf_id}' step '{step_id}' addresses_defeater_ref '{ref}' "
                            f"not found in model-defeaters.yml."
                        )

            # comparison steps must declare rival_weakness_to_own_proof as checked
            if step.get("operation") == "comparison":
                forbidden = step.get("forbidden_upgrade_checked") or []
                if not isinstance(forbidden, list) or "rival_weakness_to_own_proof" not in forbidden:
                    errors.append(
                        f"inference '{inf_id}' step '{step_id}' has operation 'comparison' but "
                        f"'rival_weakness_to_own_proof' is missing from forbidden_upgrade_checked."
                    )

    for step_id, count in Counter(all_step_ids).items():
        if count > 1:
            errors.append(f"duplicate step_id '{step_id}'.")

    for claim in claims:
        if not isinstance(claim, dict):
            continue
        if not needs_inference_entry(claim):
            continue
        cid = claim.get("claim_id")
        if isinstance(cid, str) and cid not in claims_covered:
            errors.append(
                f"claim '{cid}' (status='{claim.get('status', '?')}') requires an inference-ledger "
                f"entry, but none found in inference-ledger.yml."
            )

    # High-materiality unresolved/partially_resolved defeaters targeting strong claims
    # must have a defeater_response or uncertainty_preservation step.
    claim_by_id = {
        c.get("claim_id"): c for c in claims
        if isinstance(c, dict) and isinstance(c.get("claim_id"), str)
    }
    for defeater in defeaters:
        if not isinstance(defeater, dict):
            continue
        materiality = defeater.get("materiality")
        if not isinstance(materiality, (int, float)) or materiality < HIGH_MATERIALITY:
            continue
        if defeater.get("status") not in UNRESOLVED_DEFEATER_STATUSES:
            continue
        target_ref = defeater.get("target_claim_ref")
        if not isinstance(target_ref, str) or not target_ref:
            continue
        target_claim = claim_by_id.get(target_ref)
        if target_claim is None:
            continue
        if target_claim.get("status") not in ALL_STRONG:
            continue
        if is_exempt(target_claim):
            continue

        defeater_id = defeater.get("defeater_id", "?")
        covered = any(
            step.get("operation") in ("defeater_response", "uncertainty_preservation")
            and isinstance(step.get("addresses_defeater_refs"), list)
            and defeater_id in step["addresses_defeater_refs"]
            for inf in inferences
            if isinstance(inf, dict) and inf.get("claim_ref") == target_ref
            for step in (inf.get("inference_steps") or [])
            if isinstance(step, dict)
        )
        if not covered:
            errors.append(
                f"claim '{target_ref}' has unresolved high-materiality defeater '{defeater_id}' "
                f"(materiality={materiality}) but no inference step with 'defeater_response' or "
                f"'uncertainty_preservation' and addresses_defeater_refs containing '{defeater_id}' found."
            )

    return errors


def discover_case_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted({
        marker.parent for marker in root.rglob("claims.yml")
        if "_template" not in marker.parts
    })


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    schema = load_schema()
    case_dirs = discover_case_dirs(root)
    if not case_dirs:
        print(f"No claims.yml files found under {root}")
        return 0

    total_errors = 0
    for case_dir in case_dirs:
        errors = validate_case(case_dir, schema)
        if errors:
            print(f"FAIL {case_dir}:")
            for error in errors:
                print(f"  {error}")
            total_errors += len(errors)
        else:
            print(f"OK   {case_dir}")

    if total_errors:
        print(f"\n{total_errors} inference-ledger error(s) found.")
        return 1
    print("\nAll inference ledgers valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
