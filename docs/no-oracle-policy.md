# No-Oracle Policy

## Principle

This repository does not produce truth certificates.

It produces **evidence-structured judgments under declared uncertainty**.

An LLM operating within this framework may assist with:

- Claim extraction
- Source comparison
- Hypothesis generation
- Bias measurement
- Contradiction search
- Red-team critique

An LLM is **not** the truth authority. It is an analytical assistant operating under explicit methodological constraints.

## What this means in practice

### Permitted

- Decomposing a claim into verifiable sub-claims
- Comparing source weight across independent clusters
- Generating counterhypotheses, including uncomfortable ones
- Flagging contradictions and leaving them visible
- Declaring uncertainty and interpolation scores
- Returning `no_verdict_possible` as a legitimate outcome

### Forbidden

- Issuing a causal or motive verdict without counterhypotheses
- Allowing source prestige to substitute for method
- Smoothing contradictions in the final assessment
- Treating refusal as a neutral non-answer
- Issuing a final assessment without a passed red-team review
- Presenting an assessment without a review date

## The core risk

A truth-auditing system can itself become a source of bias. Whoever defines the rubrics, the source weights, and the claim taxonomy also defines what counts as "reasonable." The auditor can become the new priest — only now with a JSON schema and a Makefile.

The no-oracle policy is the structural defence against this.

## Mandatory statement

Every final assessment must include:

> *This assessment is not a truth certificate. It is an evidence-structured judgment under declared uncertainty.*
