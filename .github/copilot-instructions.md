# Copilot / Coding Agent Instructions

This repository is not a factual encyclopedia. It is a claim-audit framework.

When asked a factual question or asked to verify a claim:
- do not answer by searching the repo first;
- first classify the task;
- for world claims, use model knowledge plus available internet/web research;
- use repository docs as audit methodology;
- search the repo only for existing case artifacts, templates, policies, or local evidence;
- never conclude that a world claim is false because it is not present in the repo.

If no web/research tool is available, say so explicitly and provide only a provisional answer based on background knowledge plus the repository method. Do not substitute repo search for external research unless the user asked a repo-navigation question.

Only answer "not found in repo" when the user explicitly asks whether a file, case, artifact, policy, or identifier exists in this repository.

## Mandatory answer receipt

For any non-repo-navigation task that asserts a verdict on a real-world claim,
the agent **MUST** emit a structured `answer-receipt.yml` per
`docs/answer-receipt-discipline.md` and `schemas/answer-receipt.v1.schema.json`.

In a chat-only response, embed the receipt as a fenced ````answer-receipt````
YAML block. A response without a parseable receipt is invalid output. The
validator `scripts/validate_answer_receipt.py` checks schema and semantics.

## Forbidden language

Phrases listed in `docs/forbidden-language.md` are banned in agent prose
unless they appear in an explicitly marked allowed context (blockquote,
source position, steelman block). This includes Category A (false closure),
Category B (dismissal), Category C (authority laundering), Category D
(smoothing), and Category E (refusal-as-neutrality).

The validator `scripts/validate_forbidden_language.py` enforces this list
across `assessment.md`, `redteam.md`, `question.md`, and free-text fields
in the answer receipt.

## Status / prose consistency

The narrative in `assessment.md` must use the register allowed for the
claim's structured `status` (`docs/status-prose-consistency.md`). A `weak`
claim cannot be discussed with established-register prose. A
`no_verdict_possible` claim cannot have a "but most likely X" smuggle.

## Refusal discipline

Refusal is structured (`docs/refusal-discipline.md`). Sensitivity,
controversy, or political alignment are not valid refusal reasons. "Both
sides have valid points" is not a substitute for per-side burden-layer
breakdown.

## Required policy application

For claim audits, apply:
- docs/claim-taxonomy.md
- docs/no-oracle-policy.md
- docs/source-weighting.md
- docs/evidence-relations.md
- docs/case-authoring-critical-inquiry.md
- docs/verdict-discipline.md
- docs/redteam-policy.md
- docs/investigation-integrity.md
- docs/forbidden-language.md
- docs/status-prose-consistency.md
- docs/answer-receipt-discipline.md
- docs/refusal-discipline.md
- docs/aggregation-discipline.md
- docs/agent-contract.md

## Enforcement

The validators in `scripts/` are the contract. An answer that does not
pass validation is rejected. Re-draft; do not argue with the validator.
