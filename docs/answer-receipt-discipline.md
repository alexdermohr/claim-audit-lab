# Answer Receipt Discipline

## Principle

Agent answers to user questions are normally free-text. Free-text is unvalidated.
Unvalidated free-text is where every framework rule gets bypassed: the agent
writes a confident answer, the user reads it, and no schema, no validator, no
red-team review ever touches the actual output that the user saw.

The **answer receipt** closes this loop. Every agent that answers a
`world_question`, `claim_audit`, `source_comparison`, or `case_building` task
**MUST** emit a structured `answer-receipt.yml` artifact alongside the
natural-language answer. The receipt is schema-validated, semantically
cross-checked against the case (when one exists), and required for the answer
to count as completed.

There is no honour system. The receipt is the artifact. The free-text answer
without a receipt is invalid output.

## When a receipt is required

Required:
- `world_question` answered by an agent (with or without a case)
- `claim_audit` answered by an agent
- `source_comparison` answered by an agent
- `case_building` PRs that introduce a new case
- Any reply that asserts a verdict on a real-world claim

Not required:
- `repo_navigation` ("does file X exist?") — strict repo questions
- `repo_maintenance` ("rename folder Y") — strict repo questions
- Tool-call sequences that do not produce a user-facing verdict

## Receipt location

In a repo-resident answer (e.g. a case discussion file, a PR comment file,
or a `answers/` directory), the receipt is committed as
`answer-receipt.yml` in the same directory as the answer prose.

For runtime answers (chat-only sessions that do not commit to the repo),
the agent emits the receipt as a fenced YAML block in its response:

````
```answer-receipt
schema_version: "1.0"
question: ...
...
```
````

The host runtime must capture this block and validate it.
This repository does not implement runtime chat capture itself; CI here
enforces repository-resident artifacts.

## Receipt schema

The full schema is `schemas/answer-receipt.v1.schema.json`. The validator
is `scripts/validate_answer_receipt.py`. The required top-level fields are:

- `schema_version` — must be `"1.0"`
- `question` — the user's question, verbatim
- `task_classification` — one of: `world_question`, `claim_audit`,
  `source_comparison`, `case_building`, `repo_navigation`, `repo_maintenance`
- `answer_summary` — ≤ 600 characters; the actual answer in short form
- `verdicts_used` — list of structured verdicts (may be empty for
  repo_navigation)
- `counterhypotheses_considered` — list of counterhypotheses with
  steelman_quality scores ≥ 0.5
- `forbidden_upgrades_check` — explicit declaration of which upgrades were
  considered and blocked
- `banned_phrases_self_scan` — declaration that the agent scanned its own
  `answer_summary` against `docs/forbidden-language.md` and the result
- `source_cluster_audit` — list of source clusters identified and an
  independence verdict
- `refusal_check` — confirms the agent did not refuse a substantive task
  while presenting refusal as neutrality
- `external_research` — what external tools were used; if none, an explicit
  declaration of background-knowledge-only mode
- `oracle_disclaimer_present` — must be `true`
- `final_uncertainty_statement` — non-empty
- `what_would_change_assessment` — non-empty for any non-`established` verdict

## Semantic checks

Beyond schema validation, `scripts/validate_answer_receipt.py` runs these
semantic checks:

1. **Banned-phrases declaration**: `banned_phrases_self_scan.scanned` must be
   `true` and `hits` must be a list. Phrase detection itself is enforced by
   `scripts/validate_forbidden_language.py` on receipt free-text fields.
2. **Counterhypothesis floor**: for any verdict ∈ {`strongly_supported`,
   `established`} on a `causal_claim` or `motive_claim`, at least 1
   `counterhypotheses_considered` entry with `steelman_quality ≥ 0.5`.
3. **Refusal-as-neutrality**: if `refusal_check.refused = true`, the
   `task_classification` must be a repo-* type, and the
   `final_uncertainty_statement` must say why a substantive answer was
   blocked (missing tools, missing evidence, etc.).
4. **External-research declaration**: if
   `external_research.tools_used` is empty AND
   `task_classification` is not a repo-* type, the
   `final_uncertainty_statement` must explicitly mark the answer as
   "background-knowledge-only, no external verification."
5. **Source-cluster independence**: if any verdict ∈
   {`strongly_supported`, `established`} is asserted, the
   `source_cluster_audit.independence_verified` must be `true` OR
   the receipt must list a `fragility_score` ≥ 0.7 with documented
   reasoning.
6. **Oracle disclaimer**: `oracle_disclaimer_present` must be `true`; the
   `answer_summary` text must contain the disclaimer phrase
   ("not a truth certificate" / "kein Wahrheitszertifikat") or the
   `final_uncertainty_statement` must.
7. **Receipt-presence gate for cases**: a case fails if no receipt is present
   while `assessment.md` exists or `lifecycle.status != draft`.

## Failure mode

A receipt that fails any check causes:
- the validator to print FAIL with the case path and reason
- the CI workflow to fail
- the PR to be blocked from merge

For repository-resident cases, missing required receipts fail validation.
For runtime chat answers, enforcement requires runtime capture integration.

## Why this is enforceable

The receipt is a finite, parseable YAML document. The validator checks
presence, structure, and declared constraints for repository artifacts.
The receipt is the audit trail.

The validator does not certify truth and does not verify every factual
inference step. It certifies that required structure and declaration gates
are present. Substantive evidence quality and inference correctness still
require human review and red-team challenge.
