#!/usr/bin/env python3
"""Validate case-local burden-layers.yml artifacts."""

from collections import Counter
import json
import pathlib
import sys

from jsonschema_compat import jsonschema
import yaml

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "burden-layers.v1.schema.json"


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


def collect_refs(case_dir: pathlib.Path) -> tuple[set[str] | None, set[str] | None, list[str]]:
    errors: list[str] = []
    claims_data, load_errors = load_optional_object(case_dir / "claims.yml", "claims.yml")
    errors.extend(load_errors)
    evidence_data, load_errors = load_optional_object(case_dir / "evidence-pack.yml", "evidence-pack.yml")
    errors.extend(load_errors)

    claim_ids: set[str] | None = None
    if claims_data is not None:
        claims = require_list(claims_data, "claims", "claims.yml", errors)
        claim_ids = {
            item.get("claim_id") for item in claims
            if isinstance(item, dict) and isinstance(item.get("claim_id"), str)
        }

    evidence_ids: set[str] | None = None
    if evidence_data is not None:
        evidence = require_list(evidence_data, "evidence", "evidence-pack.yml", errors)
        evidence_ids = {
            item.get("evidence_id") for item in evidence
            if isinstance(item, dict) and isinstance(item.get("evidence_id"), str)
        }

    return claim_ids, evidence_ids, errors


# Statuses that indicate a layer is not yet positively established.
_OPEN_LAYER_STATUSES = {"unresolved", "partially_resolved", "contested"}
# Claim statuses that represent strong negative closure.
_NEGATIVE_CLOSURE_STATUSES = {"weak", "contradicted"}
# The layers whose openness protects the physical-mechanism thesis from knockout.
_MECHANISTIC_LAYERS = {"physical_mechanism", "structural_effect", "observational_fit"}


def _validate_anti_knockout(entry: dict, claim_by_id: dict[str, dict], errors: list[str]) -> None:
    """Emit an error when missing operational_placement alone would explain a negative verdict."""
    claim_ref = entry.get("claim_ref")
    if not isinstance(claim_ref, str) or not claim_ref:
        return
    claim = claim_by_id.get(claim_ref)
    if claim is None:
        return
    status = claim.get("status")
    if status not in _NEGATIVE_CLOSURE_STATUSES:
        return

    layers = entry.get("layers")
    if not isinstance(layers, dict):
        return

    op_layer = layers.get("operational_placement")
    if not isinstance(op_layer, dict) or op_layer.get("status") != "missing":
        return

    # Check if any mechanistic layer remains open (contested or unresolved).
    open_mechanistic = [
        name for name in _MECHANISTIC_LAYERS
        if isinstance(layers.get(name), dict) and layers[name].get("status") in _OPEN_LAYER_STATUSES
    ]
    if open_mechanistic:
        errors.append(
            f"claim '{claim_ref}' status='{status}' may not be driven by operational_placement: missing alone "
            f"while {open_mechanistic} remain open; anti-knockout rule requires independent justification "
            f"for the negative verdict or resolution of the contested mechanistic layers."
        )


def validate_case(case_dir: pathlib.Path, schema: dict) -> list[str]:
    path = case_dir / "burden-layers.yml"
    if not path.exists():
        return []

    errors: list[str] = []
    data, err = safe_load_yaml(path)
    if err:
        return [f"Could not parse burden-layers.yml: {err}"]
    if not isinstance(data, dict):
        return ["burden-layers.yml must contain a YAML object."]

    errors.extend(schema_errors(data, schema))
    entries = require_list(data, "claims", "burden-layers.yml", errors)

    refs = [entry.get("claim_ref") for entry in entries if isinstance(entry, dict) and isinstance(entry.get("claim_ref"), str)]
    for ref, count in Counter(refs).items():
        if count > 1:
            errors.append(f"duplicate burden-layer claim_ref '{ref}'.")

    claim_ids, evidence_ids, load_errors = collect_refs(case_dir)
    errors.extend(load_errors)

    # Build a claim lookup for anti-knockout checks (needs claim status).
    claims_data, _ = load_optional_object(case_dir / "claims.yml", "claims.yml")
    claim_by_id: dict[str, dict] = {}
    if isinstance(claims_data, dict):
        for claim in claims_data.get("claims") or []:
            if isinstance(claim, dict) and isinstance(claim.get("claim_id"), str):
                claim_by_id[claim["claim_id"]] = claim

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        claim_ref = entry.get("claim_ref", "?")
        if claim_ids is not None and isinstance(claim_ref, str) and claim_ref not in claim_ids:
            errors.append(f"burden-layers claim_ref '{claim_ref}' not found in claims.yml.")
        layers = entry.get("layers")
        if not isinstance(layers, dict):
            continue
        for layer_name, layer in layers.items():
            if not isinstance(layer, dict):
                continue
            evidence_refs = layer.get("evidence_refs")
            if evidence_refs is None:
                continue
            if not isinstance(evidence_refs, list):
                errors.append(f"burden-layers '{claim_ref}' layer '{layer_name}' evidence_refs must be an array.")
                continue
            for index, ref in enumerate(evidence_refs):
                if not isinstance(ref, str):
                    errors.append(f"burden-layers '{claim_ref}' layer '{layer_name}' evidence_refs[{index}] must be a string.")
                    continue
                if evidence_ids is not None and ref not in evidence_ids:
                    errors.append(
                        f"burden-layers '{claim_ref}' layer '{layer_name}' evidence_ref '{ref}' not found in evidence-pack.yml."
                    )

        _validate_anti_knockout(entry, claim_by_id, errors)

    return errors


def discover_case_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    return sorted({marker.parent for marker in root.rglob("burden-layers.yml") if "_template" not in marker.parts})


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    schema = load_schema()
    case_dirs = discover_case_dirs(root)
    if not case_dirs:
        print(f"No burden-layers.yml files found under {root}")
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
        print(f"\n{total_errors} burden-layer error(s) found.")
        return 1
    print("\nAll burden-layers valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
