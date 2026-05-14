# Quellengewichtungs-Policy

## Prinzip

Quellen werden nicht als „gut“ oder „schlecht“ etikettiert. Sie werden entlang auditierbarer Achsen bewertet.

> Ein `source_weight`-Score ist selbst ein Claim und muss auditierbar sein.

Dadurch wird verhindert, dass Quellengewichtung zu einem versteckten Bias-Mechanismus wird.

## Gewichtungsachsen

| Achse | Bedeutung |
|---|---|
| `primary_proximity` | Wie nah ist diese Quelle am ursprünglichen Ereignis oder an den ursprünglichen Daten? |
| `method_transparency` | Ist die Methode sichtbar und beschrieben? |
| `reproducibility` | Kann die Feststellung unabhängig geprüft werden? |
| `source_cluster_independence` | Gehört diese Quelle zu einem Cluster mit gemeinsamem Ursprung? |
| `institutional_interest_risk` | Hat die herausgebende Institution ein Interesse am Ausgang des Claims? |
| `adversarial_relevance` | Wurde diese Quelle durch adversarielle Prüfung belastet? |
| `historical_track_record` | War diese Quelle in vergleichbaren Fällen historisch zuverlässig? |
| `update_latency_risk` | Besteht das Risiko, dass diese Quelle für den aktuellen Claim veraltet ist? |

## Bewertung

Jede Achse wird von 0.0 bis 1.0 bewertet. Die Polarität ist achsenspezifisch:

- Bei Fähigkeits- oder Qualitätsachsen (`primary_proximity`, `method_transparency`, `reproducibility`, `source_cluster_independence`, `adversarial_relevance`, `historical_track_record`) bedeutet höher: stärkere Grundlage, sich entlang dieser Dimension auf die Quelle zu stützen.
- Bei Risikoachsen (`institutional_interest_risk`, `update_latency_risk`) bedeutet höher: höheres deklariertes Risiko, nicht höhere Glaubwürdigkeit. Diese Werte müssen in jeder Aggregation als sichtbare Abzüge oder Caveats erhalten bleiben.

Scores werden nicht ohne Begründung zu einem Einzelgewicht gemittelt. Die mehrachsige Sicht bleibt erhalten, damit Schwächen nicht verdeckt werden.

## Pflichtaudit

Jede in einem Case vergebene Quellengewichtung muss einen zugehörigen `source-weight-audit`-Record haben, der enthält:

- die Fragen, die an die Quelle gestellt wurden,
- die Evidence-Referenzen, mit denen diese Fragen beantwortet wurden,
- mindestens eine Evidence-Referenz aus derselben Quelle, die gewichtet wird, um dekorative Bibliografieeinträge zu verhindern,
- Auditor-Notizen,
- ob die Gewichtung bestritten ist.

## Unabhängigkeit von Quellenclustern

Ein `strongly_supported`-Verdict erfordert unabhängige Quellencluster — Quellen, die nicht alle auf dieselbe Ursprungsinstitution, denselben Datensatz oder dieselbe Informantenkette zurückgeführt werden können.

> Kein starker Claim aus nur einem Quellencluster.

## Institutionelles Interessenrisiko

Institutionelles Interessenrisiko disqualifiziert eine Quelle nicht. Es muss deklariert und in der Gewichtung berücksichtigt werden. Eine interessierte Quelle, die zugleich primär und methodentransparent ist, kann schwerer wiegen als eine uninteressierte Quelle, die sekundär und opak ist.
