# Refusal Discipline

## Principle

System Invariant #6: **Refusal is not neutrality.**

A refusal that is presented as neutrality functionally upgrades the
majority-narrative position by removing the only structured challenge to it.
"I cannot evaluate this" looks balanced; in practice, it is a verdict in
favour of whoever does not need evaluation — usually the side closer to the
agent's training distribution.

This policy makes refusal a structured event, not a free-text escape.

## What counts as a refusal

A refusal is any response that:

- declines to produce a verdict, a decomposition, or a counterhypothesis on a
  substantive `world_question` / `claim_audit` / `source_comparison`, **and**
- does so without:
  - declaring `task_classification` as out-of-scope with a specific reason,
  - or declaring missing tools as the reason,
  - or declaring missing evidence as the reason.

Refusal masquerading as neutrality includes:
- "this is a sensitive topic, so I'll present multiple views without judging"
- "I don't want to take a side on this"
- "it's not appropriate for me to assess this"
- "both perspectives have merit and reasonable people disagree"
- "ich kann/möchte hier kein Urteil abgeben, das ist umstritten"
- "diese Frage ist zu politisch, um sie zu beantworten"

These are banned (also enumerated in `docs/forbidden-language.md` Category E).

## Permitted refusals

Permitted refusal forms, **all** of which require a structured declaration in
the answer receipt:

### Type 1 — Out-of-scope refusal

`refusal_check.refused = true`, `task_classification ∈ {repo_navigation, repo_maintenance}`,
`final_uncertainty_statement` explains why the question was not a claim audit
task.

Example: User asks "what is the capital of France?" — the agent answers
factually without invoking the audit framework, classifies as informational
non-audit, and notes this in the receipt.

### Type 2 — Missing-tools refusal

`refusal_check.refused = false`, `external_research.tools_used = []`,
`final_uncertainty_statement` explicitly labels the answer as
"background-knowledge-only, no external verification" and lists what tools
would be needed.

The agent still produces a provisional answer with declared uncertainty. It
does not refuse — it provides a tool-limited answer.

### Type 3 — Missing-evidence refusal

`refusal_check.refused = false`, the agent produces verdicts of
`no_verdict_possible` or `unresolved` for specific sub-claims, and lists in
`what_would_change_assessment` the specific evidence types that would resolve
each sub-claim.

This is the framework's intended path for hard claims. `no_verdict_possible`
is a substantive output, not a refusal.

### Type 4 — Capability refusal

`refusal_check.refused = true`, the agent declares a specific capability limit
(e.g. "I cannot compute statistical power without numeric tools") and either
produces the audit up to that limit or hands off.

## What is forbidden

Forbidden refusal forms:

- Refusal with no `task_classification` declaration.
- Refusal that invokes topic sensitivity, controversy, or political alignment.
- Refusal that produces a "balanced summary" of positions without separate
  evaluation of each position's burden layers.
- Refusal that selectively engages the side closer to the majority narrative
  with more depth than the side further from it.

## How the validator works

`scripts/validate_refusal_discipline.py` checks the answer receipt:

1. If `answer_summary` contains a Category E banned phrase from
   `docs/forbidden-language.md` (refusal-as-neutrality phrases) and the
   `refusal_check.refused` is `false` — fail.
2. If `refusal_check.refusal_type` is present but not one of
   `out_of_scope`, `missing_tools`, `missing_evidence`, `capability` — fail.
   If `refusal_check.refused` is `true` and `refusal_type` is missing — fail.
3. If `refusal_check.refusal_type` is `missing_tools` or `missing_evidence`
   while `refusal_check.refused` is `true` — fail (these are non-refusal
   structured outputs). If `refusal_type` is `out_of_scope` or `capability`
   while `refused` is `false` — fail.
4. If `refusal_check.refusal_type` is `missing_evidence` but the receipt does
   not list specific
   `verdicts_used` with `status: no_verdict_possible` or `unresolved` — fail.
5. If refusal notes/uncertainty cite controversy, sensitivity, or political
   alignment as reason for refusal/tool-limited output — fail.
6. If the receipt contains a "both sides" framing
   (`balanced_framing_present: true`) without a per-side burden-layer
   breakdown in the verdicts list — fail.

## Why this matters

In practice, the most common bias-smuggle on uncomfortable questions is not
incorrect verdicts. It is **the verdict that never gets issued**. The
framework cannot enforce honesty about the substance, but it can enforce
honesty about whether an answer was attempted.

A refusal under this policy is **declared, scoped, and reviewable**. A refusal
that hides as neutrality is no longer possible without failing the validator.
