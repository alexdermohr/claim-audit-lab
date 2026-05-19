# Red-Team-Prüfung: Diskursintegritäts-Audit zu Lab-Origin-Hypothesen 2020–2021

**Review ID:** rt001
**Assessment ref:** cases/critical-inquiry/covid-origin-discourse-independence/assessment.md
**Status:** passed_with_notes

---

## Adversarielle Fragen

1. Konvertiert die Case Cluster-Bezogenheit des Diskurses in eine Aussage über die zugrunde liegende Ursprungsfrage?
2. Werden die Lancet- und Nature-Medicine-Artefakte als Audit-Subjekte oder als Verdict-Authority behandelt?
3. Bleibt die Unterscheidung zwischen c004 (Cluster-Effekte materially) und c005 (Mainstream-Unabhängigkeit) durchgehalten, oder kollabiert die Prosa eine in die andere?
4. Verwendet die Case selbst Kategorie-B-Dismissal-Sprache gegen die dismissive Mainstream-Position?
5. Wird die Stichprobenartigkeit von e004 hinreichend transparent gemacht?

---

## Befunde

- **f001 — medium:** Scope-Trennung zwischen Diskursaudit und Ursprungsfrage muss in question.md, c006 und assessment.md durchgehalten werden. Ohne diese Trennung wäre die Case implizit ein Verdict über die Ursprungsfrage. Fix: c006 als explizites Meta-Claim beibehalten.
- **f002 — medium:** Verdict c005=weak braucht Register-konforme Prosa. Wenn das assessment.md c005 als praktisch ausgeschlossen rahmt, wäre das ein Verdict-Cap-Bruch. Fix: Sprache "weak", "underdetermined", "schwach" verwenden; keine direkte Exklusionssprache.
- **f003 — low:** Stichprobenartigkeit von e004 ist ein Methodenrisiko. Fix: explizit benennen; corpus_level_discourse_analysis_published als Reopen-Trigger in lifecycle.yml setzen.
- **f004 — high:** Die auditierten Quellen sind in der Mainstream-Wahrnehmung Verdict-Authority. Quellenprestige-Konversion wäre unzulässig — sowohl als Stützung als auch als Verwerfung. Fix: no-oracle-policy strikt anwenden; s001-s006 als Audit-Subjekte behandeln.

---

## Selbst-Audit auf eigene Sprache

Die Red-Team-Prüfung hat das eigene Prüfdokument auf Kategorie-B-Sprache geprüft. Wo dismissive Sprache gegen die Mainstream-Position erscheinen könnte, ist sie als Source position oder als beschreibende Charakterisierung der dokumentierten Diskursartefakte markiert, nicht als Verdict der Red-Team selbst.

---

## Urteil

**Status:** passed_with_notes
**Grund:** Das Assessment hält die Scope-Trennung zwischen Diskursintegritäts-Audit und Ursprungsfrage konsistent durch. c005 trägt den Verdict-Cap "weak", obwohl die dokumentierten Cluster-Effekte stärker sind; das ist methodologisch korrekt, weil "Mainstream-Bewertung" breiter ist als die dokumentierten hochrezipierten Kanäle. Die Stichprobenartigkeit von e004 ist deklariert.

Die fortbestehende Spannung zwischen c004 und c005 (con001) ist explizit dokumentiert und nicht geglättet.
