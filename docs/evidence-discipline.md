# Evidence Discipline

## Principle

Evidence records are atomic. Each record must map to one declared source anchor.

## Source alignment

`source_ref` must match the source explicitly cited as the evidence origin within the same record.

If a record cites a different source as origin than its `source_ref`, the record is internally inconsistent and must be split or corrected.

## Cross-source reasoning placement

Cross-source synthesis is allowed, but it belongs in reasoning artifacts:

- evidence relations
- inference ledger
- assessment narrative

Do not collapse multi-source reasoning into a single atomic evidence origin.

## Reported Claims do not become World Claims

A `reported_claim` or evidence with `burden_profile: source_report` documents that a source made a statement. It does not, by itself, establish that statement as a true world fact.

### Allowed without explicit provenance:

- `reports`: Evidence documents what a source stated.
- `contextualizes`: Reported statement provides background.
- `source_position`: Explicitly marks this as a source position, not a world fact.

### Disallowed without explicit justification:

Strong relations (strength ≥ 0.6) of these types, when using report-derived evidence against world claims:

- `alternative_explanation`
- `weakens`
- `contradicts`
- `contradicts_directly`
- `contradicts_indirectly`
- `supports`
- `supports_directly`
- `supports_indirectly`
- `method_challenge`

Justification must appear in:
1. `inference-ledger.yml` with `forbidden_upgrades_checked: [reported_to_world]`, **or**
2. `argument-provenance.yml` entry with `reported_to_world` and an `allowed_effect` compatible with the relation strength.

For major-effect relations (all strong-effect relation types at strength ≥ 0.75), whichever artifact is used (`inference-ledger.yml` or `argument-provenance.yml`) must declare `allowed_effect: major_with_independent_support` and provide non-empty `independent_support_source_refs`. A bare `reported_to_world` acknowledgement does not justify high-strength world effects.

For direct `source_report`/`reported_claim` evidence entries that do not point to a reported claim id via `claim_refs`, provenance must reference the specific evidence id through `premise_evidence_refs`.

See `docs/argument-provenance-discipline.md` for details and examples.
