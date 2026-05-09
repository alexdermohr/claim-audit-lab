# Source Weighting Policy

## Principle

Sources are not labelled "good" or "bad." They are assessed along auditable axes.

> A source-weight score is itself a claim and must be auditable.

This prevents source weighting from becoming a hidden bias mechanism.

## Weight axes

| Axis | Meaning |
|---|---|
| `primary_proximity` | How close is this source to the original event or data? |
| `method_transparency` | Is the method visible and described? |
| `reproducibility` | Can the finding be independently checked? |
| `source_cluster_independence` | Does this source belong to a cluster that shares a common origin? |
| `institutional_interest_risk` | Does the source institution have a stake in the claim's outcome? |
| `adversarial_relevance` | Has this source been tested by adversarial scrutiny? |
| `historical_track_record` | Has this source been reliably accurate in comparable past cases? |
| `update_latency_risk` | Is this source at risk of being outdated for the current claim? |

## Scoring

Each axis is scored 0.0–1.0. Higher scores indicate stronger quality on that dimension.

Scores are not averaged into a single weight without justification. The multi-axis view is preserved to prevent masking weaknesses.

## Mandatory audit

Every source weight assigned in a case must have an associated `source-weight-audit` record that includes:

- The questions asked about the source
- The evidence references used to answer those questions
- Auditor notes
- Whether the weight is disputed

## Source cluster independence

A `strongly_supported` verdict requires independent source clusters — sources that cannot all be traced to a single originating institution, dataset, or informant chain.

> No strong claim from a single source cluster.

## Institutional interest risk

Institutional interest risk does not disqualify a source. It must be declared and factored into the weight. An interested source that is also primary and method-transparent may outweigh an uninterested source that is secondary and opaque.
