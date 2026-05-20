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
- `contradicts_directly`
- `supports_directly`
- `supports_indirectly`
- `method_challenge`

Strength threshold: ≥ 0.6

Then one of the following must exist:

### Option 1: Inference Ledger Entry

```yaml
inferences:
  - claim_ref: <world_claim>
    premise_claim_refs:
      - <reported_claim_id>
    forbidden_upgrades_checked:
      - reported_to_world
    inference_type: direct_premise
```

The `forbidden_upgrades_checked: [reported_to_world]` field explicitly asserts that the author has considered and justified why a source position is being used as a strong world argument.

### Option 2: Argument Provenance Entry (optional in this PR)

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
3. Check: Does `inference-ledger.yml` have an entry with `reported_to_world` checked?
4. If not: Emit error.

This blocks the semantic shortcut early, at framework level, before case content diverges.

## Evolution

This discipline is not a permanent schema requirement. As the framework matures, cases may graduate to using `argument-provenance.yml` for fine-grained argument provenance tracking. For now, `inference-ledger.yml` + `forbidden_upgrades_checked` is the minimal gate.
