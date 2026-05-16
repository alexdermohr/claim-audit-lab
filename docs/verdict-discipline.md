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

`alternative_explanation`, `weakens`, `undercuts`, and `missing_link` do not by themselves justify `contradicted`.

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

For co-causation claims, a well-supported primary explanation does not automatically falsify every possible additional cause. The audit must state whether evidence directly rules out the claim or merely leaves it unsupported relative to a better-supported hypothesis.

## Causal-chain burden

Causal claims should declare required links when the burden is non-trivial. Depending on the claim, required links may include:

- observed signal,
- provenance,
- scope,
- applicability,
- mechanism,
- timing,
- effect.

If critical links are missing, the verdict should usually be capped at `weak` or `speculative` unless direct causal evidence is present. Missing links are not the same as direct contradiction.

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
