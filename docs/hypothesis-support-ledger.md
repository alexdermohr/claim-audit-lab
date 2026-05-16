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

1. **Source content** — what a source reports, models, measures, or interprets.
2. **World claim** — whether the reported proposition is independently true under available methods and checks.
3. **Working hypothesis** — the best current interpretation under the evidence pack, uncertainty, and missing evidence.

## What the validator enforces

The validator enforces search symmetry:

- each hypothesis in `hypotheses.yml` must have exactly one support-ledger record;
- each ledger record must point to an existing hypothesis;
- evidence and source references must resolve when present;
- downgraded hypotheses must document their strongest available support, steelman, what was searched for, and what is missing for upgrade;
- empty supporting evidence requires explicit `not_found` entries.

It does **not** require every hypothesis to have equally strong evidence.

## MVP rollout note

The CLI validator scans case roots with `hypotheses.yml`. Direct `validate_case()` checks and CLI checks are strict: when `hypotheses.yml` exists, `hypothesis-support-ledger.yml` is required.

## Verdict discipline

`contradicted` requires direct incompatibility between a claim and evidence. A stronger alternative explanation, missing support, or lack of corroboration should normally produce `weak`, `speculative`, or a future `disfavored_under_current_evidence`, not `contradicted`.

For co-causation claims, a well-supported primary explanation does not automatically falsify every possible additional cause. The ledger should document whether the evidence directly rules out the claim or merely leaves it unsupported relative to a better-supported hypothesis.

## Interaction with anomaly and integrity ledgers

Hypothesis support must remain symmetric under critical inquiry. If a source or investigation strongly supports or closes a hypothesis, the case should also record material non-tests, method gaps, source-cluster dependence, and hypothesis-space gaps in the anomaly or investigation-integrity artifacts.

This does not convert anomalies into counterproof. It records closure limits: which hypotheses were genuinely weakened, which remain unresolved, and which evidentiary paths would be needed to change the support ledger.

