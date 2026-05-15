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

| Layer | Question | Example |
|---|---|---|
| Source content | What does the source report, model, measure, or interpret? | `NIST reports X.` |
| Evidence relation | How does evidence bear on a claim? | `e003 weakens c001.` |
| Hypothesis comparison | Which hypothesis is better supported under this pack? | `c008 is better supported than c001.` |
| Falsification | Is the claim directly incompatible with evidence? | `A 1953 role date contradicts a 1936 role claim.` |
| Verdict | What label follows under declared uncertainty? | `weak`, `plausible`, `contradicted` |

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

## MVP rollout note

During MVP rollout, the CLI validator checks opted-in cases with `evidence-relations.yml`. `validate_case()` remains strict for direct tests and future hardening; a later hardening PR may switch CLI discovery to all cases with `claims.yml`.

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

Causal claims should declare required links when the burden is non-trivial. A complex co-causation claim, for example, may require:

- residue or material signal,
- chain of custody,
- sufficient quantity,
- placement on relevant structural elements,
- ignition or trigger mechanism,
- temporal coupling to the event,
- structural causal effect.

If critical links are missing, the verdict should usually be capped at `weak` or `speculative` unless direct causal evidence is present. Missing links are not the same as direct contradiction.
