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

The central rule is: **alternative explanation is not contradiction; missing link is not falsification; source report is not world proof.**

## Conditional contradiction

Use `contradicts_conditionally` only when the relation depends on stated assumptions. The relation must document both `assumptions` and an `incompatible_proposition`. Without those fields, a conditional contradiction can accidentally become a hidden direct falsification.

`reports` is appropriate for `reported_claim` / `source_report` closure. It is not sufficient by itself to establish a world claim.
