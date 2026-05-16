# Anomaly Ledger

`anomaly-ledger.yml` records material anomalies that can affect a claim verdict, a hypothesis weight, or source weighting. It is a critical-inquiry artifact, not a suspicion generator.

Core rule:

> A material anomaly increases audit attention and may increase uncertainty; it does not prove manipulation, bad faith, fraud, or concealment.

## File shape

Each case may include an `anomaly-ledger.yml` with:

- `schema_version: "1.0"`
- `case_ref`
- `anomalies`, each with an `anomaly_id`, `anomaly_type`, `statement`, `materiality`, `anomaly_direction`, and `status`

High-materiality anomalies (`materiality >= 0.7`) must also document:

- why the anomaly matters;
- at least one benign explanation;
- at least one bias-risk explanation framed as a hypothesis, not a finding;
- what is missing for resolution;
- the expected verdict effect.

## Interpretation discipline

- Anomaly ≠ proof.
- Non-test ≠ cover-up.
- Missing raw data ≠ automatic falsification.
- A contradictory source must be related to a claim through evidence relations before it can change a verdict.
- High-materiality anomalies must be visible in `assessment.md`, so readers can see why confidence is limited.
- High-materiality non-tested paths recorded in `investigation-integrity.yml` must also be assessment-visible. They limit closure; they do not prove manipulation.

## Allowed anomaly classes

The schema supports general classes such as method gaps, non-tests, scope limitations, chain-of-custody gaps, unavailable raw data, model limitations, interest conflicts, hypothesis-space gaps, source-cluster dependence, unexplained exclusions, contradictory evidence, base-rate anomalies, and overstrong conclusions.

These classes are generic across official reports, academic studies, NGO reports, corporate reports, media investigations, court documents, and technical assessments.
