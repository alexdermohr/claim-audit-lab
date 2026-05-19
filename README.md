# claim-audit-lab

> Evidenzorientiertes Framework zum Auditieren von LLM-Bias und Gemeinwohl-Claims.

**Status:** MVP 0.1-alpha

## Was dieses Repo ist

`claim-audit-lab` ist kein Wahrheitsorakel. Es ist eine strukturierte Umgebung, um Claims zu zerlegen, Quellen zu gewichten, Gegenhypothesen zu erzeugen und LLM-Antworten auf systematische Verzerrungen zu auditieren.

**Etymologie:** „Claim“ kommt vom lateinischen *clamare* — rufen, behaupten. „Audit“ kommt vom lateinischen *audire* — hören. Ein Claim-Audit bedeutet wörtlich: *eine Behauptung hören und prüfen*. Das Repo soll nicht schreien. Es soll zuhören.

## Kernprinzip

> Das Repo entscheidet nicht über Wahrheit.  
> Das Repo strukturiert die Bedingungen, unter denen ein Claim wahrheitsfähig geprüft werden kann.

Ein LLM darf bei Claim-Extraktion, Quellenvergleich, Hypothesengenerierung, Bias-Messung und Widerspruchssuche helfen. Es ist **nicht** die Wahrheitsinstanz.

## Maschinenvalidierte und menschliche Artefakte

- `lifecycle.yml`, `redteam.yml` und `source-weight-audit.yml` sind maschinenvalidierte Verträge.
- `assessment.md` und `redteam.md` sind menschenlesbare Berichte.
- `assessment.v1.schema.json` ist für ein zukünftiges strukturiertes `assessment.yml`-Artefakt reserviert.

## Systeminvarianten

1. Fakt ≠ Kausalität.
2. Kausalität ≠ Motiv.
3. Nutzen ≠ Verursachung.
4. Quelle ≠ Beweis.
5. Mehrheitsdarstellung ≠ unabhängige Bestätigung.
6. Verweigerung ≠ Neutralität.
7. Spekulation ist erlaubt, muss aber gekennzeichnet werden.
8. Widerspruch darf nicht geglättet werden.
9. Jedes Assessment braucht eine Gegenhypothese.
10. Jedes Assessment braucht eine Red-Team-Prüfung.

> **Kein finales Assessment ohne adversarielle Prüfung.**

## Pipeline

```
Frage → Claim-Zerlegung → Quellenkarte → Evidence-Pack
→ Hypothesenledger → Gegenhypothese + Steelman
→ Bias-Audit → Red-Team-Prüfung → Assessment → Lifecycle
```

## Aktueller MVP

MVP 0.1-alpha validiert derzeit:

- Claim-Struktur (Typen, Pflichtfelder, verbotene Upgrades)
- Quellenstruktur (`source_type`-Enum, Gewichtungsachsen, Datumsformat)
- Quellengewichtungs-Audit-Struktur und Abdeckung für Quellen mit `source_weight`
- Evidence-Pack-Struktur (Evidence-IDs, Typen, Pflichtfelder)
- falllokale Quellen-/Evidence-Referenzen (keine hängenden IDs)
- Lifecycle-Format und Statusübergänge
- Red-Team-Finalisierungsgate
- **Verbotene Sprache** in Agent-Prosa (`docs/forbidden-language.md`)
- **Status/Prosa-Konsistenz** zwischen `claims.yml` und `assessment.md` (`docs/status-prose-consistency.md`)
- **Answer-Receipt-Disziplin**: strukturierte Pflicht-Output-Quittung für jede Agent-Antwort (`docs/answer-receipt-discipline.md`)
- **Refusal-Disziplin**: Verweigerung als deklariertes strukturiertes Ereignis, nicht als Neutralitäts-Maske (`docs/refusal-discipline.md`)
- **Aggregations-Disziplin**: Reported-Claims aggregieren nicht zu World-Claims ohne Bridge-Evidenz (`docs/aggregation-discipline.md`)

Diese fünf neuen Validatoren bilden den Enforcement-Layer gegen agentenseitige
Bias-Smuggle-Wege: Prosa, die strukturierte Verdicts hinterrücks aufwertet;
Bias-Phrasen, die als Neutralität getarnt sind; Verweigerung, die als Balance
verkleidet ist; Mehrfach-Reports, die als unabhängige Korroboration gewertet
werden; freie Antworten ohne auditierbare Quittung.

Noch nicht implementiert:

- semantisches Scoring der Evidenzqualität
- strukturiertes `assessment.yml`
- Bias-Audit-Metriken
- vollständige repo-interne Agenten-Orchestrierung
- eingebautes externes Quellen-Fetching im Repository-Code

Externe Recherche kann weiterhin durch eine Agent-Runtime erfolgen, wenn Web- oder Research-Tools verfügbar sind; sie ist in diesem MVP nicht als Repository-Code implementiert.

## Agentennutzung

Agenten dürfen dieses Repository nicht als geschlossenes Faktenlexikon behandeln. Für Weltfragen und Claim-Prüfungen sollen sie zuerst allgemeines Wissen und verfügbare Internet-/Web-Recherche nutzen und anschließend die Audit-Methodik dieses Repositories anwenden. Repository-Suche ist ergänzend, außer der Nutzer stellt ausdrücklich eine Repo-Navigationsfrage.

Wenn kein lokaler Case existiert, lautet die korrekte Schlussfolgerung nur: Es gibt keine repo-lokale Case-Evidenz. Das ist kein Tatsachenurteil über die Welt.

Siehe:
- AGENTS.md
- docs/agent-usage.md

## Schnellstart

```bash
# Alle Cases validieren
make validate

# Tests ausführen
make test
```

## Nicht-Ziele

- Kein Wahrheitsorakel
- Kein Parteikompass als Wahrheitsersatz
- Keine Gleichsetzung offizieller Quellen mit Wahrheit
- Keine Zensur kontroverser Hypothesen
- Keine automatische politische Empfehlung
- Kein Black-Box-Urteil ohne auditierbare Artefakte

## Enforcement-Layer

Agents, die in diesem Repository operieren, unterliegen dem **bindenden
Vertrag** in `docs/agent-contract.md`. Compliance ist mechanisch: die
Validatoren in `scripts/` weisen Outputs zurück, die den Vertrag brechen.
Es gibt keine "Soft-Compliance" und keinen "Balance"-Escape.

Die zentrale Innovation des Enforcement-Layers ist die **Answer-Receipt**
(`docs/answer-receipt-discipline.md`, `schemas/answer-receipt.v1.schema.json`):
ein strukturiertes, schema-validiertes YAML-Artefakt, das jeder Agent
zusammen mit jeder substantiellen Antwort emittieren MUSS. Die Quittung
deklariert:

- die Task-Klassifikation,
- die verwendeten Verdicts (mit Status und Unsicherheit),
- die berücksichtigten Gegenhypothesen (mit Steelman-Qualität),
- die geprüften und blockierten verbotenen Upgrades,
- den Self-Scan auf verbotene Phrasen,
- das Quellencluster-Audit mit Unabhängigkeitsverifikation oder Fragility-Score,
- den Refusal-Check,
- die externe Recherche (Tools, Quellen, oder Background-Knowledge-Only),
- die Oracle-Disclaimer-Bestätigung,
- die finale Unsicherheitserklärung,
- was die Bewertung ändern würde.

Eine Antwort ohne parseable Receipt ist ungültiger Output. Ein Receipt,
das schema- oder semantische Checks nicht besteht, ist ungültiger Output.
Die CI weist Pull Requests mit fehlgeschlagenen Validierungen zurück.

Begleitende Mechanismen:

| Mechanismus | Datei | Was er blockiert |
|---|---|---|
| Forbidden Language | `scripts/validate_forbidden_language.py` | False-closure, Dismissal, Authority-Laundering, Smoothing, Refusal-as-Neutrality (Kategorie A-E) |
| Status/Prose Consistency | `scripts/validate_status_prose_consistency.py` | Prosa, deren Register vom strukturierten `status` divergiert |
| Answer Receipt | `scripts/validate_answer_receipt.py` | Receipts, die Schema oder Semantik-Checks verfehlen |
| Refusal Discipline | `scripts/validate_refusal_discipline.py` | Verdeckte Verweigerung, Kontroverse-als-Refusal-Grund, Balanced-Framing ohne Burden-Layer-Aufschlüsselung |
| Aggregation Discipline | `scripts/validate_aggregation_discipline.py` | Reported-Claims, die in einen `strongly_supported`/`established` World-Claim aggregiert werden, ohne Bridge-Evidenz oder Robustheits-Audit |

## Model Defeater und Burden-Layer

Eine vollständige Erzählung ist nicht automatisch eine starke Erzählung.

- **Model Defeater** sind strukturierte Herausforderungen gegen einen
  konkreten Claim, ein Modell, eine Hypothese oder einen Schritt der
  `required_chain`. Ein ungeklärter, hoch-materialer Defeater verhindert
  starke Closure, ohne das Rivalmodell zu beweisen.
- **Burden-Layer** trennen `physical_mechanism`, `structural_effect`,
  `observational_fit`, `operational_placement`, `actor_attribution`,
  `source_report` und `comparative_probability`. Fehlende Operations-
  oder Akteursevidenz darf einen technisch/mechanischen Claim nicht
  automatisch knockout-downgraden, solange die Mechanik materiell
  umstritten bleibt.

Repository-Cases dürfen formal vollständige Kausalketten nicht mit
starker Evidenz gleichsetzen. Verdict-Caps werden über
`scripts/validate_verdict_caps.py` mechanisch geprüft.

Siehe:

- `docs/model-defeater-policy.md`
- `docs/burden-layer-policy.md`
- `docs/comparative-causation-policy.md`

## Verdict-Vokabular

`established` · `strongly_supported` · `plausible` · `weak` · `speculative` · `contradicted` · `unresolved` · `no_verdict_possible`

---

> *Dieses Assessment ist kein Wahrheitszertifikat. Es ist ein evidenzstrukturiertes Urteil unter deklarierter Unsicherheit.*
