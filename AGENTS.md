# Agent Operating Rules

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
- claim final assessment without red-team/review status.

## If web tools are unavailable
If external research tools are unavailable:
- state that external research could not be performed,
- answer only with clearly marked background knowledge and uncertainty,
- provide the source classes needed for verification,
- do not fall back to repo-only search unless the user asked a repo-navigation question.

## Required assessment language
For claim assessments, use the repository verdict vocabulary where an artifact-compatible verdict is needed:
- established
- strongly_supported
- plausible
- weak
- speculative
- contradicted
- unresolved
- no_verdict_possible

When explaining in prose, you may additionally say that a claim is "untestable with current evidence", but do not use that phrase as an artifact verdict unless a schema explicitly supports it.

Always state:
- uncertainty,
- missing evidence,
- counterhypotheses,
- source-cluster risks where relevant.
