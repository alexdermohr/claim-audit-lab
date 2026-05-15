# Hypothesis Support Ledger Policy

## Purpose

`hypothesis-support-ledger.yml` records the strongest support search performed for each hypothesis in a case. Its goal is **procedural symmetry, not evidential symmetry**: every hypothesis must be entered fairly, but the evidence does not have to be equally strong.

## Core rules

- Sources are not proofs. They are weighted evidence carriers whose proximity, method transparency, reproducibility, independence, institutional interests and adversarial relevance must remain visible.
- No claim or hypothesis status may be assigned from authority alone. A high-prestige or official source can support a claim under stated assumptions; it does not become a truth oracle.
- No hypothesis may be downgraded as `weak`, `contradicted` or `speculative` without documented active support search.
- Support search does not mean agreement. A ledger can record a strong steelman and still conclude that the hypothesis remains weak.
- False balance must be avoided. The ledger requires equal examination, not equal credibility or equal final weighting.
- Institutionally strong sources with deep methods may weigh heavily, but they remain subject to interest-risk and source-cluster checks.

## Required distinction

The ledger should keep these levels separate:

1. **Source reports X** — established by the source text if accurately captured.
2. **X is technically or historically true** — requires method review, independent checks, and adversarial comparison.
3. **X is the best current working hypothesis** — allowed under an evidence pack, but still contingent on missing evidence and uncertainty.

## What the validator enforces

The validator enforces search symmetry:

- each hypothesis in `hypotheses.yml` must have exactly one support-ledger record;
- each ledger record must point to an existing hypothesis;
- evidence and source references must resolve when present;
- downgraded hypotheses must document their strongest available support, steelman, what was searched for, and what is missing for upgrade;
- empty supporting evidence requires explicit `not_found` entries.

It does **not** require every hypothesis to have equally strong evidence.

## MVP rollout note

During MVP rollout, the CLI validator checks opted-in cases with `hypothesis-support-ledger.yml`. `validate_case()` remains strict for direct tests and future hardening; a later hardening PR may switch CLI discovery to all cases with `hypotheses.yml`.

## Verdict discipline

`contradicted` requires direct incompatibility between a claim and evidence. A stronger alternative explanation, missing support, or lack of corroboration should normally produce `weak`, `speculative`, or a future `disfavored_under_current_evidence`, not `contradicted`.

For co-causation claims, a well-supported primary explanation does not automatically falsify every possible additional cause. The ledger should document whether the evidence directly rules out the claim or merely leaves it unsupported relative to a better-supported hypothesis.
