# Evidence Relations

`evidence-relations.yml` records typed relations between evidence and claims. It prevents the audit from treating all negative evidence as direct contradiction.

Relation types are:

- `reports`
- `supports_directly`
- `supports_indirectly`
- `weakens`
- `undercuts`
- `contradicts_directly`
- `contradicts_conditionally`
- `contextualizes`
- `alternative_explanation`
- `missing_link`
- `method_challenge`
- `source_interest_warning`

The central rule is: **alternative explanation is not contradiction; missing link is not falsification; source report is not world proof.** Direct contradiction requires direct incompatibility. A stronger alternative explanation, missing link, non-test, source-report non-corroboration, or bounded absence claim may weaken or cap confidence, but must not by itself produce `contradicted` for a co-causation/world-causal claim.

## Conditional contradiction

Use `contradicts_conditionally` only when the relation depends on stated assumptions. The relation must document both `assumptions` and an `incompatible_proposition`. Without those fields, a conditional contradiction can accidentally become a hidden direct falsification.

`reports` is appropriate for `reported_claim` / `source_report` closure. It is not sufficient by itself to establish a world claim.


## Direct contradiction boundary

Use `contradicts_directly` only when the evidence and claim cannot both be true under the claim scope. Do not encode “no evidence found,” “not corroborated,” “method gap,” “missing causal bridge,” or “better explanation” as `contradicts_directly`; use `weakens`, `undercuts`, `missing_link`, `method_challenge`, `alternative_explanation`, or a bounded `absence_claim` instead.
