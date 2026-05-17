# Verdict Discipline

## Purpose

Verdict discipline prevents the audit pipeline from turning source authority, missing support, or a stronger competing explanation into an over-strong final label. The lab should ask which epistemic operation is being performed before it assigns a verdict.

## Core invariants

1. Source ≠ proof.
2. Reported claim ≠ world claim.
3. Alternative explanation ≠ contradiction.
4. Missing evidence ≠ falsification.
5. Weak support ≠ falsehood.
6. Official source ≠ truth oracle.
7. `contradicted` requires direct incompatibility between claim and evidence.
8. Causal claims require explicit causal-chain or burden analysis when they approach strong verdicts.
9. Every hypothesis gets active support search before downgrade.
10. Verdict severity must be traceable to typed evidence relations, not prose confidence alone.

## Epistemic layers

The audit should keep these layers separate:

| Layer | Question |
|---|---|
| Source content | What does the source report, model, measure, or interpret? |
| Evidence relation | How does evidence bear on a claim? |
| Hypothesis comparison | Which hypothesis is better supported under the current evidence pack? |
| Falsification | Is the claim directly incompatible with evidence? |
| Verdict | What label follows under declared uncertainty? |

## Claim-kind precedence

When `claim_type` and `claim_kind` both appear, verdict-discipline logic treats `claim_kind` as the operative epistemic layer. `claim_type` remains a broad taxonomy label, but `claim_kind` controls whether a rule is evaluating a reported/source claim, a world-causal claim, or a comparative claim.

## Relation discipline

Typed relations should distinguish direct contradiction from weaker operations:

- `reports`: a source states, models, measures, or summarizes something.
- `supports_directly`: evidence directly supports the target claim.
- `supports_indirectly`: evidence supports a premise or component but not the full claim alone.
- `weakens` / `undercuts`: evidence lowers confidence or challenges an assumption.
- `contradicts_directly`: evidence is directly incompatible with the claim.
- `contradicts_conditionally`: evidence contradicts the claim under a stated assumption.
- `contextualizes`: evidence supplies scope or background.
- `alternative_explanation`: evidence supports a competing explanation without logically falsifying the target.
- `missing_link`: evidence documents a missing burden-chain element.
- `method_challenge`: evidence challenges method, sampling, or inference.
- `source_interest_warning`: evidence or metadata flags source-role risk.

`alternative_explanation`, `weakens`, `undercuts`, `missing_link`, method gaps, non-tests, non-corroboration, and bounded absence findings do not by themselves justify `contradicted`.

## Discovery rule

Any case with both `claims.yml` and `evidence-pack.yml` must include `evidence-relations.yml`. Verdict discipline is a required gate for such cases, not an opt-in check.

## Verdict rules

- `established`: source content, or a world claim with strong and appropriately independent support.
- `strongly_supported`: multiple methodically strong and sufficiently independent support clusters.
- `plausible`: explanatory fit with remaining uncertainty.
- `weak`: some support exists, but the evidentiary chain is incomplete or the claim is worse supported than competitors.
- `speculative`: mostly interpretive or suspicion-based support.
- `contradicted`: direct incompatibility with strong evidence.
- `unresolved`: materially open or conflicting evidence.
- `no_verdict_possible`: the current pack cannot evaluate the claim.

For co-causation claims, a well-supported primary explanation does not automatically falsify every possible additional cause. The audit must state whether evidence directly rules out the claim or merely leaves it unsupported relative to a better-supported hypothesis. Direct contradiction requires direct incompatibility. A stronger alternative explanation, missing link, non-test, source-report non-corroboration, or bounded absence claim may weaken or cap confidence, but must not by itself produce `contradicted` for a co-causation/world-causal claim.

## Causal-chain burden

Causal claims should declare required links when the burden is non-trivial. Depending on the claim, required links may include:

- observed signal,
- provenance,
- scope,
- applicability,
- mechanism,
- timing,
- effect.

If critical links are missing, the verdict should usually be capped at `weak` or `speculative` unless direct causal evidence is present. Missing links are not the same as direct contradiction. When a `causal_claim` uses `burden_profile: causal_chain` and reaches `strongly_supported`, `established`, or `contradicted`, `required_chain` must be present and non-empty so validators can identify which causal link is being closed or ruled out.

## Critical-inquiry closure discipline

Strong verdicts must not be created by source prestige alone. A claim can be strongly supported only when the evidence relation, source weight, anomaly coverage, and investigation-integrity burden are all consistent with that level of closure.

Important separations:

- A source-content claim (`claim_kind: reported_claim`) says what a source reports; it does not by itself close the corresponding world claim.
- A material anomaly can prevent overconfidence without proving manipulation.
- A non-test can limit the closure burden without implying concealment.
- Official, advocacy, corporate, academic, media, court, and technical sources are all evaluated by the same closure discipline.

High-materiality anomalies that affect a claim must be visible in `assessment.md`, and high-risk/high-adversarial sources used for strong world claims must be covered by `investigation-integrity.yml`. High-materiality non-tested paths from investigation-integrity must also be assessment-visible; a non-test limits closure but does not prove manipulation.


## Contradiction and co-causation discipline

`contradictions.yml` is the place where unresolved, weighted, scoped, or logically resolved conflicts remain visible. Its existence does not itself change a claim verdict; verdict movement still requires typed evidence relations and a compatible burden profile.

For co-causation language such as “contributed,” “co-cause,” or “mitverursachte,” a stronger alternative explanation is not enough to mark the claim `contradicted`. Direct incompatibility must be documented explicitly with `direct_incompatibility_basis`; prose in `notes` is not sufficient.


## Source-cluster robustness

Source weight is not source immunity. A verdict that is strong on paper can still be fragile: if removing one dominant source cluster collapses the verdict, the verdict depends on that cluster, not on independent evidence.

The `source-cluster-robustness.yml` artifact is **optional for low-stakes or draft cases** but **mandatory when `investigation-integrity.yml` declares `source_cluster_refs` and at least one `causal_claim` carries a `strongly_supported`, `established`, or `contradicted` status**. Its purpose is to separate four ideas the audit must not blur:

- **interest risk**: a source has structural reasons to lean one way (already modeled via `source_weight` / `investigation-integrity.yml`);
- **cluster dependency**: a verdict relies on a small set of related sources;
- **compromise scenario**: a *stress assumption* that the cluster is institutionally entangled, applied as a what-if, not a finding;
- **verdict fragility**: how much the verdict moves when the dominant cluster is removed in a knockout test.

When a `causal_claim` reaches `strongly_supported`, `established`, or `contradicted` and `investigation-integrity.yml` flags one or more source clusters, the case must declare the dominant cluster(s) and at least one knockout test for them in `source-cluster-robustness.yml`. All sources flagged by `investigation-integrity.yml` for a strong causal claim must be fully covered by declared clusters; partial coverage is not enough. If any knockout test reports `fragility_score >= 0.7`, `assessment.md` must surface the cluster dependency / fragility in plain text.

**A knockout test is a fragility measurement, not a proof of the counter-hypothesis.** It answers: "how much does the verdict depend on this cluster?" — not "is the cluster wrong?" or "is the alternative true?" Compromise scenarios are stress hypotheses, not proofs. A compromise scenario may never be used as positive evidence for a counter-hypothesis. An official cluster does not automatically win because it is official; an anti-official cluster does not automatically win because it is adversarial. The validator does not decide which source is true; it enforces that strong verdicts make their cluster dependence visible.

## Overclosure guard

The overclosure validator blocks direct-negative verdicts that are really weaker operations under another label. `contradicts_directly` must not be used when the explanation or `incompatible_proposition` only says that a stronger alternative explanation exists, positive evidence was not found, a causal bridge is missing, an official source did not corroborate the proposition, or a method/non-test gap remains.

For co-causation claims marked `contradicted`, the case must identify a required-chain link and explain why that link is directly excluded, impossible, or incompatible. A stronger main cause can justify `weak` or `speculative`; it is not enough for negative closure.

If a high-materiality anomaly affects a contradicted world-causal claim, or an unresolved high-materiality non-tested path overlaps that claim through the investigation source cluster, negative closure requires explicit residual-path closure. The current validator emits a conservative targeted failure for overlapping non-tested paths because dedicated `affected_claims` and residual-path-closure fields are intentionally left for a later schema expansion.
