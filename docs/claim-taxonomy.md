# Claim Taxonomy

## Overview

Claims are typed before they are assessed. Type determines which evidence requirements, which counterhypotheses, and which forbidden logical jumps apply.

## Claim types

### `factual_event_claim`
A claim about an event, location, date, or action.

*Requires:* primary source, timeline  
*Forbidden upgrade:* absence of evidence to falsehood

---

### `statistical_claim`
A claim involving a number, quota, budget, survey, or dataset.

*Requires:* method/dataset reference, sample description  
*Forbidden upgrade:* correlation to causation

---

### `legal_claim`
A claim about a law, ruling, regulation, or jurisdiction.

*Requires:* primary legal source (text of law, court document)  
*Forbidden upgrade:* source prestige to truth

---

### `causal_claim`
A claim that A causes B.

*Requires:* timeline, mechanism, at least two counterhypotheses  
*Forbidden upgrades:* correlation to causation, benefit to motive

---

### `motive_claim`
A claim that an actor intended X.

*Requires:* actor interest + capability + timeline  
*Forbidden upgrades:* benefit to motive, suspicion to proof

---

### `capability_claim`
A claim that an actor could have done X.

*Requires:* evidence of access, authority, or technical ability  
*Forbidden upgrade:* suspicion to proof

---

### `beneficiary_claim`
A claim that an actor benefited from X.

*Requires:* demonstrable advantage, not mere possibility  
*Forbidden upgrade:* benefit to motive

---

### `narrative_claim`
A claim that a particular interpretation is being spread, amplified, or normalised.

*Requires:* distribution evidence, amplification mechanism  
*Forbidden upgrade:* narrative presence to factual truth

---

### `suppression_claim`
A claim that an interpretation is being excluded, taboo-ised, or delegitimised.

*Requires:* documented exclusion pattern, not just absence  
*Forbidden upgrade:* absence of evidence to falsehood

---

### `forecast_claim`
A prediction about a future development.

*Requires:* declared model, base-rate reference, uncertainty score  
*Forbidden upgrade:* plausibility to certainty

---

### `value_claim`
A normative judgement.

*Requires:* explicit normative framework  
*Forbidden upgrade:* value claim to factual claim

---

### `meta_claim`
A claim about bias, source availability, or discourse structure.

*Requires:* structural evidence, not just assertion  
*Forbidden upgrade:* meta-claim to factual claim about object level

---

## Forbidden upgrades (universal)

These logical jumps are forbidden in all claim types:

| Forbidden upgrade | Example |
|---|---|
| Correlation → causation | "It happened after X, therefore X caused it." |
| Benefit → motive | "They gained from it, so they planned it." |
| Source prestige → truth | "The official body said it, so it is true." |
| Suspicion → proof | "It looks suspicious, so they did it." |
| Absence of evidence → falsehood | "We found no proof, so it didn't happen." |

## Claim-kind closure boundaries

### `reported_claim`

`claim_kind: reported_claim` means the auditable proposition is “source X reports Y.” A strong verdict may be appropriate when the source content is clear, but that closes only the report-content question. It must not be treated as a direct verdict on the world claim Y. If Y is assessed as true or false, create a separate world claim and connect it through its own evidence relations.

A `reported_claim` must use `burden_profile: source_report` so validators can distinguish source-content closure from world-claim closure.

### `absence_claim`

`claim_kind: absence_claim` means “no matching evidence was found inside a declared scope,” not “the thing exists nowhere.” The claim must declare that scope, such as the current evidence pack, a named source, or a named dataset, and must guard against `absence_of_evidence_to_falsehood`.

Absence-language trigger terms (for example "nicht nachgewiesen", "kein Nachweis", "no evidence", "not documented") require classification as `absence_claim`.

In schema v1, `absence_scope` is represented as a string field, not an object.

Strong closure for absence claims (`established` or `strongly_supported`) requires explicit exhaustivity markers and `evidence_refs` that show what was searched.

`forbidden_upgrades` must include `absence_of_evidence_to_falsehood` for absence claims.
