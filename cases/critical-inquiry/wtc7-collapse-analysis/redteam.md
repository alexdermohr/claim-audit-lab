# Red-Team-Bericht: WTC 7 — Einsturzmechanismus

**Review ID:** rt001
**Assessment-Referenz:** cases/critical-inquiry/wtc7-collapse-analysis/assessment.md
**Reviewer:** assistant-redteam
**Reviewed at:** 2026-05-19

---

## Zweck

Dieser Bericht dokumentiert die adversarielle Überprüfung des WTC-7-Assessments. Ziel ist die Identifikation ungeprüfter Annahmen, methodisch schwach rekonstruierter Gegenhypothesen und unzulässiger Verdictaufwertungen.

---

## Frage 1: Absence-Claim und H1-Stützung

Das Assessment verwendet die Abwesenheit physikalischer CD-Evidenz (c006) als Teil des Verdicts für c001 (P(CD) > P(Brand) ist ungesützt). Risiko: Absence-of-evidence wird als evidence-of-absence verwendet.

**Befund:** c006 ist explizit als scope-begrenzter Abwesenheitsclaim formuliert. Im inference-ledger (inf001) ist der Schritt als "comparison" markiert, nicht als "exclusion". Die Schlussfolgerung lautet: H2 hat keine positive Mechanismusbasis — nicht: H2 ist ausgeschlossen. Das Register ist korrekt.

---

## Frage 2: NIST als Audit-Subjekt vs. Verdict-Authority

NIST ist eine US-Bundesbehörde, deren Bericht die Hauptquelle für H1 ist. Risiko: Quellenprestige wird in Wahrheit konvertiert.

**Befund:** Das Assessment behandelt NIST als Audit-Subjekt mit dokumentierten methodischen Schwächen (c004). Die source-weight-audit gibt institutional_interest_risk: 0.65. Das Verdict für c005 (plausibel, nicht strongly_supported) reflektiert die fehlende Replikation. Keine unzulässige Prestige-Konversion identifiziert.

---

## Frage 3: UAF-Studie steelmanned?

Die UAF-Hulsey-Studie ist AE911Truth-finanziert. Risiko: Sie wird wegen des Interessenkonflikts zu früh abgetan, ohne ihren stärksten Einwand zu rekonstruieren.

**Befund:** Im hypothesis-support-ledger (h2) und in model-defeaters (d001) wird der UAF-Befund als hoch-materialer Defeater für H1 behandelt (Materialität 0.55). Der Steelman für H1 (hypotheses.yml) benennt explizit den UAF-Befund als stärksten Einwand. Die Studie wird nicht ausgeblendet. Die Finanzierungsproblematik ist deklariert, ohne die Studie deshalb zu verwerfen.

---

## Frage 4: Operational-Placement-Burden und Absence-of-Evidence

c007 (CD-Vorbereitung operativ extrem komplex) könnte als versteckter Absence-of-Evidence-Upgrade gelesen werden.

**Befund:** c007 ist als Burden-Layer-Claim (operative Komplexität) strukturiert, nicht als Ausschlussclaim. Die Formulierung ist "operativ ungesützt", nicht "operativ unmöglich". Das burden-layers.yml für c001 listet operational_placement als "missing" — das ist korrekt und kein Upgrade zu "false". Der forbidden_upgrade absence_of_evidence_to_falsehood ist in c006 und c007 explizit gelistet.

---

## Frage 5: Historischer Einzelfall

WTC 7 ist der erste dokumentierte Stahl-Hochhauseinsturz primär durch Feuer. Risiko: Diese Einzigartigkeit wird zugunsten H1 untergewichtet.

**Befund:** Das anomaly-ledger (a002) behandelt den Präzedenzfall-Mangel als "contextualizes_uncertainty" mit Materialität 0.60. Die Bias-Achse im assessment.md rekonstruiert explizit den H2-freundlichen Rahmen, der diesen Punkt stärker gewichtet. c005 ist auf "plausible" begrenzt — teilweise wegen des Einzelfallcharakters. Die Gewichtung ist methodisch korrekt.

---

## Gesamturteil

Das Assessment hält die Methodengrenzen des claim-audit-lab Frameworks ein:

- c001 ist korrekt auf `weak` begrenzt.
- c005 ist korrekt auf `plausible` begrenzt.
- c003 ist korrekt auf `speculative` begrenzt.
- Absence-Claims sind scope-begrenzt.
- Steelmans für H1 und H2 sind vorhanden.
- NIST wird nicht als Wahrheitsinstanz behandelt.
- Keine forbidden-language-Treffer identifiziert.

Befund `passed_with_notes`: Die under-steelmanning-Risiken sind adressiert. Keine blocking findings.

---

> *Dieses Assessment ist kein Wahrheitszertifikat. Es ist ein evidenzstrukturiertes Urteil unter deklarierter Unsicherheit.*
