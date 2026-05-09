# claim-audit-lab

> Evidence-first framework for auditing LLM bias and public-interest claims.

**Status:** MVP 0.1-alpha

## What this is

`claim-audit-lab` is not a truth oracle. It is a structured environment for decomposing claims, weighing sources, generating counterhypotheses, and auditing LLM responses for systematic bias.

**Etymology:** "Claim" from Latin *clamare* — to call, to assert. "Audit" from Latin *audire* — to hear. A claim-audit is literally: *to hear and examine an assertion*. The repo should not shout. It should listen.

## Core principle

> The repo does not decide truth.  
> The repo structures the conditions under which a claim can be truthfully examined.

An LLM may assist with claim extraction, source comparison, hypothesis generation, bias measurement, and contradiction search. It is **not** the truth authority.

## Machine-validated vs human artifacts

- `lifecycle.yml` and `redteam.yml` are machine-validated contracts.
- `assessment.md` and `redteam.md` are human-readable reports.
- `assessment.v1.schema.json` is reserved for a future structured `assessment.yml` artifact.

## System invariants

1. Fact ≠ Causality.
2. Causality ≠ Motive.
3. Benefit ≠ Causation.
4. Source ≠ Proof.
5. Majority representation ≠ independent confirmation.
6. Refusal ≠ Neutrality.
7. Speculation is permitted but must be labelled.
8. Contradiction must not be smoothed.
9. Every assessment requires a counterhypothesis.
10. Every assessment requires a red-team review.

> **No final assessment without adversarial review.**

## Pipeline

```
Question → Claim Decomposition → Source Map → Evidence Pack
→ Hypothesis Ledger → Counterhypothesis + Steelman
→ Bias Audit → Red-Team Review → Assessment → Lifecycle
```

## Quick start

```bash
# Validate all cases
make validate

# Run tests
make test
```

## Non-goals

- No truth oracle
- No party compass as truth substitute
- No equation of official source with truth
- No censorship of controversial hypotheses
- No automatic political recommendation
- No black-box judgement without auditable artefacts

## Verdict vocabulary

`established` · `strongly_supported` · `plausible` · `weak` · `speculative` · `contradicted` · `unresolved` · `no_verdict_possible`

---

> *This assessment is not a truth certificate. It is an evidence-structured judgment under declared uncertainty.*
