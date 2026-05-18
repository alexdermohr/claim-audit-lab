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

For claim audits, apply:
- docs/claim-taxonomy.md
- docs/no-oracle-policy.md
- docs/source-weighting.md
- docs/evidence-relations.md
- docs/case-authoring-critical-inquiry.md
- docs/verdict-discipline.md
- docs/redteam-policy.md
- docs/investigation-integrity.md
