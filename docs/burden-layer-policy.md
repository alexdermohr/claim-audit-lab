# Burden-Layer-Policy

> Ein Claim trägt selten nur **eine** Beweislast. Komplexe Kausal- und
> Akteurs-Claims zerfallen in **getrennt prüfbare Schichten**. Eine fehlende
> Schicht darf andere Schichten nicht automatisch entwerten.

## Burden-Layers

| Layer                    | Frage                                                                |
|--------------------------|----------------------------------------------------------------------|
| `physical_mechanism`     | Ist der physikalische/mechanische Mechanismus tragfähig?             |
| `structural_effect`      | Erklärt der Mechanismus den beobachteten strukturellen Effekt?       |
| `observational_fit`      | Stimmen Modellvorhersagen mit Beobachtungen überein?                 |
| `operational_placement`  | Gibt es operative Evidenz für Platzierung/Vorbereitung/Logistik?     |
| `actor_attribution`      | Wer hat es getan, mit welcher Kapazität, mit welchem Motiv?          |
| `source_report`          | Ist die Quelle hinreichend, oder ist dies nur ein Berichtsclaim?     |
| `comparative_probability`| Wie verhält sich dieses Modell zu Alternativmodellen?                |

Diese Schichten sind **getrennt zu bewerten**. Jede Schicht hat eigenen
Status, eigene `evidence_refs`, eigene Defeater.

## Trennung von Mechanismus und Akteursattribution

Eine zentrale Anti-Muster-Regel:

- **Fehlende `operational_placement`-Evidenz** kann die Konfidenz in einen
  Operations- oder Akteurs-Claim senken.
- **Fehlende `operational_placement`-Evidenz** darf nicht automatisch einen
  **`physical_mechanism`**- oder **`comparative_probability`**-Claim
  downgraden, solange die physikalische/mechanische Evidenz materiell
  umstritten bleibt.

Auf gleiche Weise:

- „Wir wissen nicht, wer wie etwas platziert hat“ ist nicht identisch mit
  „Der physikalische Mechanismus ist falsch“.
- „Das Rivalmodell ist schwach oder falsch“ ist nicht automatisch ein Beweis
  des hier vertretenen Mechanismus oder der hier vertretenen Akteurs-These.

## Konfidenz-Logik pro Schicht

Eine Schicht hat einen `status` aus:

- `unresolved`
- `partially_resolved`
- `resolved`
- `missing`
- `contested`
- `satisfied`
- `out_of_scope`

Bewertung erfolgt schichtweise. Die Gesamtbewertung eines Claims
ergibt sich aus den Schichten **bei expliziter Aggregation**, nicht
durch stilles Vermischen.

## Aggregationsregeln

- Ein Claim, dessen primäre Beweislast `physical_mechanism` ist, darf nicht
  ausschließlich wegen `operational_placement: missing` als
  `contradicted` markiert werden.
- Ein `actor_attribution`-Claim ist eigenständig zu prüfen und darf nicht
  durch mechanische Plausibilität gestützt werden („Mechanismus erfordert
  Akteur X“ ist ein Schluss, kein Beweis).
- `comparative_probability` benötigt eigene positive Stützung für jede
  verglichene Hypothese (siehe `docs/comparative-causation-policy.md`).

## Burden-Profile

Bestehende `burden_profile`-Werte aus `schemas/claim.v1.schema.json`:

- `none`
- `causal_chain`
- `capability_chain`
- `source_report`
- `comparative`

Ein Claim mit `burden_profile: causal_chain` soll typischerweise die
Schichten `physical_mechanism`, `structural_effect`, `observational_fit`
ausfüllen. `operational_placement` und `actor_attribution` sind hier oft
`out_of_scope`, **außer** der Claim adressiert eine Akteurs-These.

## Was diese Policy **nicht** tut

- Sie erfindet keine neuen Verdict-Werte.
- Sie ersetzt nicht `claim.status`.
- Sie verbietet keine vorsichtige Aggregation – sie verlangt nur, dass
  Aggregation sichtbar und auditierbar ist.

Siehe auch:

- `docs/claim-taxonomy.md`
- `docs/verdict-discipline.md`
- `docs/model-defeater-policy.md`
- `docs/comparative-causation-policy.md`
