# Agent Usage

## Core distinction
claim-audit-lab is a method repository, not a complete factual knowledge base.
Agents should use:
- model knowledge and internet/web research for world facts,
- repository docs for audit method,
- repository cases for local case evidence,
- repository schemas and validators for artifact correctness.

## Task modes

| User task | First action | Repo role |
|---|---|---|
| Normal factual question | Answer using knowledge + web if available | Method only |
| Claim verification | Use external research when available; otherwise state the limitation, classify claim, apply method | Method + optional case lookup |
| Source comparison | Compare cited/external sources | Source-weighting method |
| Case scaffold | Use templates and schemas | Artifact generation |
| Repo navigation | Search repository | Primary source |

## Forbidden answer pattern
Do not answer a world question with:
"Not found in this repository."

Correct replacement:
"No local case artifact was found in this repository. I will assess the claim using available external evidence, or state what external evidence is still needed, and apply the repository's audit method."

## Example prompts
- "Prüfe die Behauptung: ..."
- "Bewerte diese Quelle nach claim-audit-lab-Methodik: ..."
- "Welche Evidenz bräuchte man, um diese These zu prüfen?"
- "Erstelle ein Case-Scaffold für diese politische Behauptung."
- "Ist diese Aussage kausal überzogen?"
- "Suche im Repo, ob es zu Claim X bereits einen Case gibt."

## Output discipline for claim audits
A good answer should separate:
- claim,
- claim type,
- evidence used,
- evidence missing,
- source quality,
- contradictions,
- alternative hypotheses,
- provisional verdict,
- uncertainty,
- next verification step.
