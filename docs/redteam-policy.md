# Red-Team Policy

## Principle

Every assessment must survive adversarial review before it becomes final.

A red-team that never blocks is a theatre critic who calls every play "interesting."

> `redteam.status == passed` — or — `assessment.status != final`

## Structure

A red-team review asks:

1. What assumption does the assessment carry unspoken?
2. Which source was weighted too strongly?
3. Which counterhypothesis was reconstructed too weakly?
4. Where does the assessment jump from benefit to motive?
5. Where does source prestige replace methodological scrutiny?
6. Which politically inconvenient interpretation was dismissed too early?

## Finding severity

| Severity | Meaning |
|---|---|
| `low` | Minor gap; does not block; must be noted |
| `medium` | Significant gap; requires response or explicit acknowledgement |
| `high` | Blocks finalisation; requires fix before status can move to `final` |

## Verdict states

| Status | Meaning |
|---|---|
| `passed` | No high-severity findings; assessment may proceed to final |
| `blocked` | One or more high-severity findings; assessment cannot be finalised |
| `passed_with_notes` | No blocking findings; medium or low findings noted |

## Hard rule

A `blocked` red-team verdict means `assessment.status` cannot be `final`. This is enforced by the validation scripts.

## Reviewer independence

Self-review is allowed as an intermediate control step, but it cannot produce an independent pass verdict.

`passed` and `passed_with_notes` require independent review.

When reviewer independence is not established, use `self_review_only` or `pending_independent_review`.

## Finding resolution discipline

High-severity findings block pass-style verdicts until they are explicitly resolved.

A high finding is only considered resolved when its status is `resolved` and `resolution_refs` point to concrete remediation artifacts.

## What red-team is not

Red-team review is not:

- A search for ideological balance for its own sake
- A requirement to treat all hypotheses as equally valid
- A veto mechanism for uncomfortable conclusions that are well-supported

Red-team review is a structural adversarial pass that asks whether the evidence and reasoning can withstand challenge. If they can, they survive. If they cannot, they must be revised.

## Meta-red-team

The red-team process itself is subject to audit. If red-team reviewers consistently fail to block assessments on particular political topics, or consistently block assessments on others, this pattern is itself a signal that requires attention.
