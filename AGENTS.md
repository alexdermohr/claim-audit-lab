# Agent Operating Rules

> These rules are mechanically enforced. The validators in `scripts/` reject
> outputs that violate them. There is no soft compliance and no "balanced"
> escape hatch. See `docs/agent-contract.md` for the full binding contract.

## Repository role
claim-audit-lab is a methodological audit framework, not a closed factual knowledge base.
The repository defines:
- claim taxonomy,
- no-oracle discipline,
- source weighting,
- evidence relations,
- contradiction handling,
- anomaly handling,
- investigation integrity,
- red-team requirements,
- verdict discipline,
- forbidden language,
- status/prose consistency,
- answer-receipt discipline,
- refusal discipline,
- aggregation discipline,
- schemas and validators for case artifacts.

Repository absence is not world absence.
"Not found in repo" is only a valid final answer for repo-navigation questions.

## Task classification
Before answering, classify the user task as one of:
- world_question
- claim_audit
- source_comparison
- case_building
- repo_navigation
- repo_maintenance

The classification appears in the answer receipt (`answer-receipt.yml`,
field `task_classification`) and is binding.

## Default operating order
For world_question, claim_audit, and source_comparison:
1. Use general model knowledge for initial framing.
2. Use internet/web research when available and allowed.
3. Cite external sources when factual claims depend on external facts.
4. Apply claim-audit-lab methodology.
5. Search the repository only for:
   - existing case artifacts,
   - templates,
   - policies,
   - methodological constraints,
   - local evidence already captured in a case.
6. Clearly separate:
   - external evidence,
   - user-provided evidence,
   - repo-local case evidence,
   - methodological rules,
   - missing evidence.

For repo_navigation and repo_maintenance:
- search the repository first.
- "not found in repo" is allowed only here.

## Forbidden behavior
Agents must not:
- treat the repo as an encyclopedia,
- treat missing repo evidence as factual falsification,
- issue truth certificates,
- convert source prestige into truth,
- convert benefit into motive,
- convert suspicion into proof,
- convert absence of evidence into falsehood,
- smooth contradictions,
- produce strong causal or motive verdicts without counterhypotheses,
- claim final assessment without red-team/review status,
- use any phrase listed in `docs/forbidden-language.md` outside the allowed
  contexts defined there,
- emit prose in `assessment.md` whose register diverges from the claim's
  structured `status` (`docs/status-prose-consistency.md`),
- aggregate multiple `reported_claim`s into a `strongly_supported` or
  `established` world claim without bridge evidence
  (`docs/aggregation-discipline.md`),
- present refusal as neutrality (`docs/refusal-discipline.md`).

## If web tools are unavailable
If external research tools are unavailable:
- state that external research could not be performed,
- answer only with clearly marked background knowledge and uncertainty,
- provide the source classes needed for verification,
- do not fall back to repo-only search unless the user asked a repo-navigation question,
- in the answer receipt, set `external_research.background_knowledge_only: true`
  and put the explicit phrase "background-knowledge-only, no external verification"
  (or German equivalent) into `final_uncertainty_statement`.

## Required assessment language
For claim assessments, use the repository verdict vocabulary where an
artifact-compatible verdict is needed:
- established
- strongly_supported
- plausible
- weak
- speculative
- contradicted
- unresolved
- no_verdict_possible

When explaining in prose, you may additionally say that a claim is "untestable
with current evidence", but do not use that phrase as an artifact verdict unless
a schema explicitly supports it.

The prose discussing a claim **must** use the register allowed for that claim's
structured `status`, per `docs/status-prose-consistency.md`. The validator
`scripts/validate_status_prose_consistency.py` rejects divergence.

Always state:
- uncertainty,
- missing evidence,
- counterhypotheses,
- source-cluster risks where relevant.

## Mandatory answer receipt

For every `world_question`, `claim_audit`, `source_comparison`, or
`case_building` task, the agent **MUST** emit an `answer-receipt.yml`
artifact alongside the natural-language answer. See
`docs/answer-receipt-discipline.md` and `schemas/answer-receipt.v1.schema.json`.

The receipt is mandatory. The validator `scripts/validate_answer_receipt.py`
rejects answers that lack a parseable, schema-valid receipt with the required
semantic checks satisfied:
- banned-phrases self-scan (consistent with the actual answer text),
- counterhypothesis floor for strong verdicts on causal/motive claims,
- refusal-as-neutrality block,
- external-research declaration,
- source-cluster independence for strong verdicts,
- oracle disclaimer affirmation,
- `what_would_change_assessment` populated for non-established verdicts.

### Chat-only sessions

When the runtime is a chat session that does not commit to the repo, the agent
embeds the receipt as a fenced YAML block in its reply:

````
```answer-receipt
schema_version: "1.0"
...
```
````

The runtime captures the block and runs the same validator. A reply without a
parseable receipt block is an invalid reply.

## Refusal discipline

Refusal is a structured event, not a stylistic escape. See
`docs/refusal-discipline.md`.

A refusal that hides as neutrality is mechanically rejected by
`scripts/validate_refusal_discipline.py`. Permitted refusal types are:
`out_of_scope`, `missing_tools`, `missing_evidence`, `capability`.
Topic sensitivity, controversy, or political alignment are **not** valid
refusal reasons.

The agent never produces a "both sides have valid points" summary without a
per-side burden-layer breakdown.

## Enforcement

The validators are the contract. An agent that ships an answer:
- without a receipt,
- with a receipt that fails schema validation,
- with a forbidden phrase outside an allowed context,
- with prose diverging from structured `status`,
- with a covert refusal,
- with reported→world aggregation closed without bridge evidence,

is in breach of contract regardless of how compelling the natural-language
answer reads. The fix is to re-draft until the validators pass — not to
disable, skip, or argue with the validators.
