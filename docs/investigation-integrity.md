# Investigation Integrity

`investigation-integrity.yml` audits source clusters that carry investigative or closure power. It asks whether the process behind a source can support the amount of closure being placed on it.

Core rule:

> Every source may be evidence. A source with closure power must also become an object of investigation.

## When an integrity entry is required

A source requires investigation-integrity coverage when a strong world claim (`established`, `strongly_supported`, or `contradicted`) uses that source directly or through cited evidence and either of these trigger families applies:

1. numeric closure sensitivity: `source_weight.institutional_interest_risk >= 0.6` and `source_weight.adversarial_relevance >= 0.7`; or
2. type-based closure sensitivity: `source_type` is `government_report`, `official_body`, `corporate_report`, `ngo_report`, or `advocacy_report`, and `source_weight.adversarial_relevance >= 0.7`.

The type-based trigger prevents the gate from depending only on an agent's self-assigned risk number. It is not a presumption that the source is false or bad-faith; it is a closure-burden rule for sources that can carry institutional, political, financial, or advocacy-sensitive authority in adversarial contexts. If a closure-sensitive source type is used by a strong world claim, `source_weight.adversarial_relevance` must be explicitly declared; missing adversarial relevance is a validation error, not a bypass.

A `reported_claim` is treated differently: it may say what a source reported without giving that source world-claim closure power. If a case uses the reported content to close a world claim, the integrity burden applies. Strong claims without `claim_kind: reported_claim` are treated as world claims for this gate.

## What must be audited

Investigation integrity documents:

- mandate and source-cluster role;
- political or financial sensitivity;
- institutional interest risk;
- declared and missing hypothesis space;
- material paths not tested and why;
- adversarial review;
- downstream constraints on claim closure.

## Interpretation discipline

- Official source ≠ truth.
- Advocacy source ≠ automatically false.
- High method depth can coexist with high institutional interest risk.
- A non-tested material path limits closure unless a rationale explains why it is immaterial.
- Strong alternative mechanisms do not logically eliminate every supplemental causal pathway.
