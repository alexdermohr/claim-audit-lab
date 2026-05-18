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

## Verdict-Vokabular

`established` · `strongly_supported` · `plausible` · `weak` · `speculative` · `contradicted` · `unresolved` · `no_verdict_possible`

---

> *Dieses Assessment ist kein Wahrheitszertifikat. Es ist ein evidenzstrukturiertes Urteil unter deklarierter Unsicherheit.*
