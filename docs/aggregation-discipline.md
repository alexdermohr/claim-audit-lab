# Aggregation Discipline

## Principle

Multiple `reported_claim`s do not aggregate into a `world_claim`.

If five sources report event X, the structured fact is: "five sources report
event X." It is **not**: "event X is established." The transition from
reported to world is a burden-layer transition, not an aggregation.

This is a frequent bias-smuggle path: collect a small set of cluster-aligned
reports, then close on the underlying world claim as if reports were the
verdict.

## What is allowed

Allowed inferences from multiple reported claims:

- **Existence of a reporting pattern**: "Sources S1, S2, S3 report X" is
  itself a `factual_event_claim` about the discourse.
- **Cluster identification**: if S1, S2, S3 are not independent, the
  `source_cluster_audit` notes this and treats the reports as one cluster
  for evidentiary purposes.
- **Bridge claims**: a `reported_claim` may **bridge** to a world claim only
  through the burden layers (`physical_mechanism`, `observational_fit`,
  `actor_attribution`, etc.) — not by counting.

## What is forbidden

Forbidden aggregations:

- "Multiple credible sources confirm X, so X is established" — count is not a
  burden layer.
- "Mainstream consensus reports X" — count + cluster, still not a burden
  layer.
- "All major outlets agree on X" — count + cluster alignment, treated as if
  it were independent corroboration.
- "Independent sources S1..Sn each confirm X" without prior verification of
  independence (no `source_cluster_robustness` artifact for that claim).

## Required structure for reported-to-world transitions

To upgrade from a `reported_claim` (or set of them) to a `world_claim` of
status `strongly_supported` or higher, the case must contain:

1. A `burden-layers.yml` entry for the world claim with all relevant layers
   addressed by **non-reported** evidence — i.e. evidence that itself is not
   a report-of-a-report.
2. A `source-cluster-robustness.yml` fragility test demonstrating that the
   verdict does not collapse if any single source cluster is removed.
3. An explicit `bridge_evidence` field in `evidence-relations.yml` linking
   each reported_claim to the world_claim, with relation type other than
   `reports` (e.g. `supports_directly`, `supports_indirectly`).

## How the validator works

`scripts/validate_aggregation_discipline.py` checks every claim with
`claim_type` in {`causal_claim`, `factual_event_claim`, `narrative_claim`}
and `status` in {`strongly_supported`, `established`}:

1. Collect the claim's `evidence_refs`.
2. Resolve each evidence to its `evidence_type` in `evidence-pack.yml`.
3. Resolve each evidence to its relation type via `evidence-relations.yml`.
4. If ≥ 80% of the resolved relations are `reports` (the relation type used
   for "this source reports X"), the validator requires the case to contain
   either:
   (a) at least one non-`reports` relation supporting the same claim, OR
   (b) a `source-cluster-robustness.yml` entry for the claim with
       `independence_verified: true`.
5. If neither is present, the claim fails: it is a counted-reports
   aggregation, not a structurally supported world claim.

## Examples

### Bad

```yaml
# claims.yml
- claim_id: c001
  claim_type: factual_event_claim
  status: established
  evidence_refs: [e001, e002, e003, e004, e005]
```

```yaml
# evidence-relations.yml
- claim_ref: c001
  evidence_ref: e001
  relation_type: reports
- claim_ref: c001
  evidence_ref: e002
  relation_type: reports
- claim_ref: c001
  evidence_ref: e003
  relation_type: reports
- claim_ref: c001
  evidence_ref: e004
  relation_type: reports
- claim_ref: c001
  evidence_ref: e005
  relation_type: reports
```

This fails: 100% `reports` relations, no bridge evidence, no robustness
artifact.

### Good

```yaml
# evidence-relations.yml
- claim_ref: c001
  evidence_ref: e001
  relation_type: reports
- claim_ref: c001
  evidence_ref: e002
  relation_type: reports
- claim_ref: c001
  evidence_ref: e006
  relation_type: supports_directly
  notes: "Primary archival document, not a report."
```

This passes if `e006` is a non-`reports` relation type and qualifies as
bridge evidence under the source-weight audit.

## Why this matters

LLMs trained on news corpora overweight `reports` evidence by default. The
training signal "many outlets say X" is treated as a positive truth signal,
even when the outlets are within one source cluster (e.g. wire-service
reposts, official-quote chains, narrative chains).

This validator forces the framework's burden-layer model into the
aggregation step. Reports remain reports. The transition to world must be
carried by mechanism, observation, or attribution evidence — not by count.
