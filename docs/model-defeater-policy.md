# Model-Defeater-Policy

> Ein **Model Defeater** ist eine strukturierte Herausforderung gegen einen
> spezifischen Claim, ein Modell, eine Hypothese oder einen einzelnen Schritt
> einer `required_chain`. Er verhindert, dass eine vollständige Erzählung mit
> ungeklärten zentralen Widersprüchen automatisch als starker Schluss
> behandelt wird.

## Was ein Model Defeater ist

Ein Model Defeater ist mehr als gewöhnliche Gegenevidenz. Er adressiert nicht
einfach „eine Quelle widerspricht der anderen“, sondern bezeichnet ein
konkretes Modellproblem:

- eine Inkompatibilität zwischen Beobachtung und Modellvorhersage,
- eine fehlende Annahmen- oder Sensitivitätsanalyse für einen zentralen
  Modellschritt,
- eine fehlende unabhängige Reproduktion eines zentralen Modellschritts,
- ein konkurrierendes Modell, dessen zentrale Annahmen ohne Begründung
  ignoriert wurden,
- eine offene Datenlücke, die das Modell strukturell trägt.

Ein Defeater zielt **immer** auf ein konkretes Ziel:

- einen `claim_id`,
- eine `hypothesis_id`,
- einen `required_chain`-Schritt,
- oder die Kombination dieser Bezüge.

## Defeater vs. gewöhnliche Gegenevidenz

| Gewöhnliche Gegenevidenz                     | Model Defeater                                                  |
|----------------------------------------------|-----------------------------------------------------------------|
| widerspricht einem Detail                    | trifft eine zentrale Annahme oder einen Kernschritt             |
| kann durch Triangulation gemildert werden    | bleibt verdict-relevant, solange er ungeklärt ist               |
| reduziert Konfidenz                          | kann Closure verhindern, ohne das Rivalmodell zu beweisen       |
| muss nicht modellspezifisch sein             | adressiert eine identifizierbare Schwachstelle eines Modells    |

## Wirkung auf Verdicts

Ein offener, hoch-materialer Defeater **verhindert starke Closure**, auch
wenn ansonsten eine vollständige narrative Kette vorliegt. „Starke
Closure" umfasst dabei **beide Richtungen**:

- starke positive Closure (`established`, `strongly_supported`),
- starke negative Closure (`contradicted`).

Das `verdict_effect.effect`-Feld unterscheidet:

- `prevents_strong_closure` — blockiert beide Richtungen (Standardwert).
- `prevents_strong_positive_closure` — blockiert nur Hochstufung.
- `prevents_strong_negative_closure` — blockiert nur Überwiderlegung.
- `downgrades_confidence` — senkt Konfidenz, ohne ein konkretes Verdict
  zu blocken.
- `context_only` — dokumentiert eine Spannung ohne unmittelbare
  Verdict-Wirkung.

**Kernregel:**

> Ein Claim darf eine starke Closure-Bewertung (`strongly_supported`,
> `established`) weder erhalten noch behalten, allein weil eine vollständige
> Kausalkette dokumentiert ist, wenn ungeklärte hoch-materiale Defeater
> zentrale Kettenschritte herausfordern und keine adäquate Rebuttal-Evidenz
> hinterlegt ist.

„Vollständige Kausalkette“ ist nicht gleich „wahre Kausalkette“. Eine Kette
kann formal vollständig sein und trotzdem an einer entscheidenden Stelle
unbelegt, unreproduziert oder modellinkompatibel sein.

## Warum Defeater verdict-relevant bleiben

- „Niemand hat das Gegenmodell sauber beschrieben“ entwertet einen Defeater
  nicht; er bleibt strukturell sichtbar.
- Ein Defeater fordert den Claim heraus, nicht die Welt.
- Ein Defeater muss kein Rivalmodell beweisen, um ein starkes Schluss-Verdict
  zu verhindern.
- Resolution eines Defeaters verlangt **Rebuttal-Evidenz**, nicht bloß
  Wiederholung der ursprünglichen Behauptung.

## Materialität

`materiality` ist ein Wert in `[0, 1]`:

- `>= 0.75`: zentral; verhindert starke Closure ohne Rebuttal.
- `0.50–0.74`: ernsthafte Schwächung; erfordert dokumentierte Behandlung.
- `< 0.50`: kontextuell; wird vermerkt, blockt aber kein Verdict.

## Status-Vokabular

Verträglich mit bestehender Konvention:

- `unresolved`
- `partially_resolved`
- `resolved`
- `out_of_scope`

## Abstrakte Beispiele (Platzhalter, keine realen Fälle)

- *„Modell M behauptet Mechanismus A. Beobachtung B ist mit M inkompatibel,
  ohne dass M auf B angepasst wurde.“*
- *„Kettenschritt `s_propagation` wird nur durch eine Quelle getragen, die
  Annahmen nicht offenlegt.“*
- *„Hypothese H ignoriert eine alternative Hypothese H', deren zentrale
  Annahme nicht widerlegt wurde.“*

## Was diese Policy **nicht** tut

- Sie ersetzt keine inhaltliche Recherche.
- Sie macht Defeater nicht zu Beweisen ihrer Rivalmodelle.
- Sie verwandelt Verdacht nicht in Beweis.
- Sie ersetzt das No-Oracle-Prinzip nicht.

Siehe auch:

- `docs/no-oracle-policy.md`
- `docs/verdict-discipline.md`
- `docs/burden-layer-policy.md`
- `docs/comparative-causation-policy.md`
