# Argument Provenance Discipline

## Purpose

An argument is not automatically valid just because multiple sources or agents repeat it.

When a claim is *reported* by a source (as a `reported_claim` or through `source_report` burden profile), that claim documents what the source said. It does not, by itself, establish that claim as a true statement about the world.

## The Error

The semantic shortcut that must be blocked:

```
Source reports statement X
  ↓
X becomes a strong world argument, defeater, or alternative explanation
```

This bypasses the epistemological boundary between:
- **Source position** (what was said)
- **World argument** (evidence bearing on truth)

## Allowed Relations without Explicit Provenance

For evidence derived from reported claims, these relation types are permitted without additional justification:

- `reports`: The evidence documents what a source stated.
- `contextualizes`: The reported statement provides background context.
- `source_position`: Explicitly marks this as reporting a source's position, not a world fact.

## Strong Relations Require Provenance

If a report-derived evidence is used with a strong effect against or for a world claim:

Relation types:
- `alternative_explanation`
- `weakens`
- `contradicts`
- `contradicts_directly`
- `contradicts_indirectly`
- `supports`
- `supports_directly`
- `supports_indirectly`
- `method_challenge`

Strength threshold: ≥ 0.6

Major-effect threshold: ≥ 0.75 for all strong-effect relation types listed above. At or above that threshold, `reported_to_world` alone is not enough in either `inference-ledger.yml` or `argument-provenance.yml`: the matching entry must use `allowed_effect: major_with_independent_support` and provide non-empty `independent_support_source_refs`.

For `major_with_independent_support`, each `independent_support_source_refs` id must exist in `sources.yml`. Independence must be verifiable against known origin sources: either explicit `origin_source_refs` in the provenance object, or origin sources derived from the referenced report-derived evidence (`source_ref` / `source_refs`). If origin sources are unknown, major-effect independent support is invalid.

Then one of the following must exist:

### Option 1: Inference Ledger Entry

The validator supports two formats within `inference-ledger.yml`:

**Top-level form** (direct premise declaration):

```yaml
inferences:
  - claim_ref: <world_claim>
    premise_claim_refs:
      - <reported_claim_id>
    forbidden_upgrades_checked:
      - reported_to_world
    inference_type: direct_premise
```

**Nested form** (using `inference_steps`, the standard case artifact format):

```yaml
inferences:
  - claim_ref: <world_claim>
    inference_steps:
      - step_id: "step001"
        premise_claim_refs:
          - <reported_claim_id>
        forbidden_upgrade_checked:
          - reported_to_world
        operation: corroboration
        produces: "Justification for using reported claim as world argument"
```

Both `forbidden_upgrades_checked` (plural) and `forbidden_upgrade_checked` (singular) are accepted in either format.

The presence of `reported_to_world` in the checks explicitly asserts that the author has considered and justified why a source position is being used as a strong world argument. For major-effect relations (≥ 0.75), this check is necessary but insufficient without the matching major-effect fields.

### Option 2: Argument Provenance Entry

When a single `inference-ledger.yml` entry is insufficient, an optional `argument-provenance.yml` can document the full argument structure:

```yaml
arguments:
  - argument_id: arg_001
    target_claim_ref: <world_claim>
    premise_claim_refs:
      - <reported_claim_id>
    origin_source_refs:
      - <source_id>
    origin_cluster_refs: []
    role: "non_decisive_defeater" | "burden_layer_open" | "uncertainty_preserver" | "major_defeater"
    allowed_effect: "non_decisive" | "uncertainty_only" | "major_with_independent_support"
    forbidden_upgrades_checked:
      - reported_to_world
    independent_support_source_refs: [...]  # required if allowed_effect: major_with_independent_support
```

Both `forbidden_upgrades_checked` (plural) and `forbidden_upgrade_checked` (singular) are accepted.

`reported_to_world` is a necessary check, not a free pass. For major-effect relations at strength ≥ 0.75, `allowed_effect: non_decisive` does not justify the relation. In that range the argument must use `allowed_effect: major_with_independent_support`, and `independent_support_source_refs` must be a non-empty list.

## Evidence Field Support

The validator supports both `evidence_ref` (singular string) and `evidence_refs` (list) in evidence-relations entries. When both are present, they are merged and deduplicated.

Evidence is detected as report-derived when either its `claim_refs` list contains a `reported_claim` id, or the evidence entry itself is marked with `burden_profile: source_report` / `claim_kind: reported_claim`. For direct source-report evidence without a reported claim ref, provenance must reference the specific evidence id via `premise_evidence_refs`.

## Rationale

1. **Transparency**: The agent or author explicitly acknowledges that a reported claim is being used as a world argument, not merely as a source position.

2. **Auditability**: Future reviewers can trace exactly which reported claims contribute to which verdicts.

3. **Generality**: The same rule applies to all reported claims, regardless of source prestige or consensus.

4. **Decoupling**: Source credibility assessment is separate from world-argument effect. A highly credible source can still report a claim that remains speculative or open in terms of world truth.

## Examples

### Fail (without provenance)

```yaml
# claims.yml
claims:
  - claim_id: c_demolition
    statement: "WTC 7 collapsed due to controlled demolition"
    claim_type: causal_claim

  - claim_id: c_nist_fire
    statement: "NIST concluded fire caused the collapse"
    claim_kind: reported_claim

# evidence-pack.yml
evidence:
  - evidence_id: e_nist_report
    claim_refs: [c_nist_fire]

# evidence-relations.yml
relations:
  - relation_id: r_alt_explanation
    claim_ref: c_demolition
    evidence_refs: [e_nist_report]
    relation_type: alternative_explanation
    strength: 0.74
```

**Problem**: The NIST report is used as a strong alternative explanation (strength=0.74) to support c_nist_fire against c_demolition, but c_nist_fire is marked as `reported_claim`. No `inference-ledger.yml` entry justifies this strong world effect.

**Fix**: Add to `inference-ledger.yml`:

```yaml
inferences:
  - claim_ref: c_demolition
    premise_claim_refs: [c_nist_fire]
    inference_type: direct_premise
    forbidden_upgrades_checked: [reported_to_world]
    notes: |
      NIST's fire hypothesis is used here as a strong defeater for the demolition claim
      because NIST's engineering assessment is subject to cross-examination and
      independent structural analysis, not merely because NIST said it.
```

### Pass

```yaml
# Same structure as above, but with inference-ledger entry:
inferences:
  - claim_ref: c_demolition
    premise_claim_refs: [c_nist_fire]
    forbidden_upgrades_checked: [reported_to_world]
```

## Integration with Validators

The validator `validate_reported_claim_world_effect.py` enforces this discipline:

1. For each `reported_claim` or `source_report`-burden claim.
2. For each strong relation (strength ≥ 0.6) using report-derived evidence.
   - Both `evidence_ref` (singular) and `evidence_refs` (list) are supported.
3. Check inference-ledger.yml (top-level or nested inference_steps) for `reported_to_world` plus matching premises (`premise_claim_refs` or `premise_evidence_refs` for direct source-report evidence).
4. Check argument-provenance.yml for a valid argument entry with `reported_to_world` and matching premises (`premise_claim_refs` or `premise_evidence_refs`).
5. For major-effect relations at strength ≥ 0.75, require `major_with_independent_support` plus independent support source refs in whichever artifact is used.
6. If neither: Emit error.

This blocks the semantic shortcut early, at framework level, before case content diverges.

## Evolution

This discipline is not a permanent schema requirement. As the framework matures, cases may graduate to using `argument-provenance.yml` for fine-grained argument provenance tracking. Both `inference-ledger.yml` and `argument-provenance.yml` are supported as justification mechanisms.
