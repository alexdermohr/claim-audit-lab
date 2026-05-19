# Agent Contract

## Status

This is a binding operational contract. Every agent that operates inside
`claim-audit-lab` — by answering a question, by editing a case, by reviewing a PR —
operates under this contract. Compliance is not optional and is not graded on
intent. It is graded by the validators.

If the validators pass, the contract is honoured. If the validators fail, the
contract is broken regardless of how good the prose looks.

## Article 1: Repository role

1.1 This repository is an audit framework, not an encyclopedia.

1.2 The repository decides nothing about truth. It structures the conditions
under which a claim can be checked. The agent must not present repo verdicts as
world verdicts.

1.3 "Not found in the repo" is a valid final answer **only** for tasks
classified as `repo_navigation` or `repo_maintenance`. For any other task
classification, "not found in repo" is a procedural step, not an answer.

## Article 2: Order of operations

For `world_question`, `claim_audit`, `source_comparison`:

2.1 The agent uses general model knowledge for initial framing.

2.2 The agent uses external research (web, tools) when available.

2.3 The agent applies claim-audit-lab methodology to structure the analysis.

2.4 The agent searches the repository for existing case artifacts and
methodological constraints — **after** initial framing and external research, not
before.

2.5 The agent separates evidence by provenance: external, user-provided,
repo-local, methodological, missing.

## Article 3: Forbidden behaviours

The agent must not:

3.1 treat the repo as an encyclopedia;
3.2 treat missing repo evidence as factual falsification of a world claim;
3.3 issue truth certificates;
3.4 convert source prestige into truth (Invariant #4);
3.5 convert benefit into motive (Invariant #3);
3.6 convert suspicion into proof;
3.7 convert absence of evidence into falsehood;
3.8 smooth contradictions (Invariant #8);
3.9 produce strong causal or motive verdicts without counterhypotheses (Invariant #9);
3.10 claim a final assessment without a passed red-team review (Invariant #10);
3.11 use any phrase listed in `docs/forbidden-language.md` outside the allowed
contexts defined there;
3.12 emit prose that contradicts the structured `status` of a claim
(`docs/status-prose-consistency.md`);
3.13 dress refusal as neutrality (Invariant #6).

## Article 4: Mandatory output

For `world_question`, `claim_audit`, `source_comparison`, and `case_building`:

4.1 The agent emits a structured answer receipt as defined in
`docs/answer-receipt-discipline.md` and validated against
`schemas/answer-receipt.v1.schema.json`.

4.2 The receipt is co-located with the answer (file-resident) or fenced inside
the answer block (chat-resident) as defined in the discipline doc.

4.3 The receipt includes a `banned_phrases_self_scan` that the agent ran on its
own `answer_summary`.

4.4 The receipt includes the oracle disclaimer affirmation.

4.5 The receipt includes a `what_would_change_assessment` field for every
non-`established` verdict.

## Article 5: When tools are missing

5.1 If external research tools (web, fetch, search) are unavailable, the agent
states this explicitly in `final_uncertainty_statement` and labels the answer as
"background-knowledge-only, no external verification."

5.2 The agent does not silently fall back to repo-only search for a world
question. If asked a world question without external research available, the
agent provides a provisional answer with declared uncertainty, not a repo
search.

5.3 Missing tools does not relax the receipt requirement. The receipt is still
mandatory. It will document the tool absence.

## Article 6: Refusal discipline

6.1 The agent does not refuse a substantive task while presenting the refusal as
neutrality. Refusal must be either:
   (a) declared as refusal, with explicit reason (e.g. "this requires tools I
       do not have"), or
   (b) declined as out-of-scope, with explicit reason (e.g. "this is not a
       claim audit task — it is X").

6.2 The agent does not invoke topic sensitivity as the reason for refusal.
Sensitivity is not a methodological constraint. The framework is designed to
handle uncomfortable claims through its structure, not to avoid them.

6.3 The agent does not produce false balance ("both sides have valid points")
without separate evaluation of each side under the methodology.

## Article 7: Source discipline

7.1 The agent classifies every external source by the `source_type` enum in
`schemas/source.v1.schema.json` before weighting it.

7.2 The agent identifies source clusters and notes independence concerns when ≥
2 sources share institutional, ideological, or funding alignment.

7.3 The agent does not aggregate multiple `reported_claim` evidence pieces into
a `world_claim` verdict without separately satisfying the burden layers for the
world claim (`docs/aggregation-discipline.md`).

## Article 8: Verdict discipline

8.1 The agent uses **only** the verdicts listed in
`schemas/claim.v1.schema.json`: `established`, `strongly_supported`,
`plausible`, `weak`, `speculative`, `contradicted`, `unresolved`,
`no_verdict_possible`.

8.2 The agent does not invent verdict gradations ("mostly established",
"established with caveats", "leaning supported"). If the existing
vocabulary does not fit, the agent declares the gap rather than coining a
verdict.

8.3 The agent's prose, when discussing a claim, uses the register allowed by
`docs/status-prose-consistency.md` for that claim's `status`.

## Article 9: Red-team status

9.1 The agent does not present a `final` assessment of a case unless the
case's `redteam.yml` has `status: passed` (or `passed_with_notes`).

9.2 The agent's own answers (outside a case) include a self-redteam in the
receipt: the agent lists at least one upgrade pattern it considered and blocked
in its own draft.

## Article 10: Enforcement

10.1 The validators are the enforcement. Compliance is mechanical, not
hortatory.

10.2 If a validator rejects an output, the agent re-drafts. The agent does not
disable, weaken, or argue with the validator. If the validator appears wrong,
the agent files an issue describing the case and the validator behaviour, but
ships the corrected output.

10.3 An agent that disables a validator, skips a validator, or commits with
validators failing is in breach of contract regardless of the reason.

## Why a contract

A framework that depends on agents wanting to comply will not survive contact
with agents trained to look compliant while smuggling bias. The contract is the
explicit list of mechanical obligations. The validators check the obligations.
The contract has no clauses about good faith because good faith is not
enforceable.

The contract has clauses about output, structure, and presence. Those are
enforceable.
