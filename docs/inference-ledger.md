# Inference Ledger

## Purpose

The inference ledger is the explicit, step-by-step derivation chain that connects evidence to a strong or contentious verdict. It makes the epistemic path auditable: instead of prose-implied reasoning, each operative move is named, grounded in specific evidence or claim refs, and checked for forbidden upgrades.

The ledger does not change verdicts. It documents why a verdict already assigned is derivable from the evidence present in the case — or why the derivation is uncertain but preserved rather than closed.

## When a ledger entry is required

An entry is required for a claim when any of the following is true:

| Condition | Trigger |
|---|---|
| `status: established` or `status: strongly_supported` | `triggered_by: strong_positive_verdict` |
| `status: contradicted` | `triggered_by: strong_negative_verdict` |
| `burden_profile: causal_chain` or `comparative` AND status is not `unresolved` / `no_verdict_possible` | `triggered_by: causal_chain` or `comparative_claim` |
| Unresolved high-materiality defeater (≥ 0.75) targeting a strong claim | Requires a `defeater_response` or `uncertainty_preservation` step in the corresponding inference |

## Exemptions

| Exemption | Condition |
|---|---|
| `claim_kind: reported_claim` | A source-report claim only asserts what a source stated; the inference chain belongs to the world claim, not the report claim. |
| `burden_profile: source_report` | Same as above at the burden-profile level. |
| `claim_type: meta_claim` | Case-constitutive scope declarations are analytically prior to the evidence chain; requiring a derivation chain for them is circular. |

## Schema

`schemas/inference-ledger.v1.schema.json`

Top-level fields:
- `schema_version`: `"1.0"`
- `case_ref`: identifies the case (e.g. `"cases/history/mccloy-nazi-finance-support"`)
- `inferences`: array of inference entries

### Inference entry

| Field | Type | Notes |
|---|---|---|
| `inference_id` | string | Pattern `^inf[0-9]{3,}$`; must be unique within the case |
| `claim_ref` | string | Must match a `claim_id` in `claims.yml` |
| `triggered_by` | enum | See table above |
| `inference_steps` | array | At least one step required |

### Inference step

| Field | Type | Required | Notes |
|---|---|---|---|
| `step_id` | string | yes | Pattern `^step[0-9]{3,}$`; case-local unique |
| `premise_evidence_refs` | array[string] | no | Must reference existing `evidence_id` values in `evidence-pack.yml`; **requires `evidence-pack.yml` to be present** |
| `premise_claim_refs` | array[string] | no | Must reference existing `claim_id` values in `claims.yml` |
| `operation` | enum | yes | See operations table below |
| `produces` | string | yes | One-line summary of what the step concludes; min 1 character |
| `uncertainty_effect` | enum | yes | `raises`, `lowers`, `preserves`, `localizes` |
| `forbidden_upgrade_checked` | array[enum] | no | List upgrades the author explicitly considered and blocked |
| `addresses_defeater_refs` | array[string] | conditional | Required when operation is `defeater_response` or `uncertainty_preservation` and a high-materiality unresolved/partially_resolved defeater must be explicitly addressed; each value must match a `defeater_id` in `model-defeaters.yml` |
| `notes` | string | no | Authoring notes |

### Operations

| Operation | Use when |
|---|---|
| `corroboration` | Multiple evidence items converge on the same conclusion |
| `contradiction` | Evidence directly rules out an alternative |
| `comparison` | Claim verdict rests on being better-supported than a rival; **must** include `rival_weakness_to_own_proof` in `forbidden_upgrade_checked` |
| `exclusion` | Scope, timing, or mechanism logically excludes a rival path |
| `scope_limit` | Evidence bounds the claim but does not close it |
| `defeater_response` | Step explicitly responds to a specific defeater |
| `uncertainty_preservation` | Documents irreducible uncertainty instead of falsely resolving it |

## Validator

`scripts/validate_inference_ledger.py cases`

Checks:
1. Schema validity
2. `claim_ref` exists in `claims.yml`
3. Every step must have at least one non-empty `premise_evidence_refs` or `premise_claim_refs` (enforced by schema and validator).
4. `premise_evidence_refs` require `evidence-pack.yml` to be present; each ref must match an existing `evidence_id`.
5. `premise_claim_refs` exist in `claims.yml`
6. `inference_id` and `step_id` are case-locally unique
7. Every claim that requires a ledger entry has one
8. High-materiality unresolved/partially_resolved defeaters targeting strong claims must have a `defeater_response` or `uncertainty_preservation` step whose `addresses_defeater_refs` contains the exact `defeater_id` — a generic response without that field does not satisfy the gate.
9. `comparison` steps declare `rival_weakness_to_own_proof` in `forbidden_upgrade_checked`

## Authoring notes

- The ledger is not a narrative. Each step should be one sentence in `produces`.
- `uncertainty_preservation` is not defeat. Documenting an open question is stronger than hiding it in prose.
- `comparison` is the highest-risk operation. The validator enforces that the author has checked `rival_weakness_to_own_proof`. A claim is not stronger because its rival is weaker; it is stronger because its own evidence chain is stronger.
- A step with neither `premise_evidence_refs` nor `premise_claim_refs` is invalid.
- A ledger entry for a `weak` causal-chain claim will typically use `uncertainty_preservation` with `uncertainty_effect: preserves` — this is the correct honest record of a bounded but unresolved derivation.
