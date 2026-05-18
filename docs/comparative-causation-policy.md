# Comparative-Causation-Policy

> Vergleichende Claims wie *„Modell A erklärt das Ereignis besser als Modell B“*
> oder *„X ist wahrscheinlicher als Y“* erfordern eigene Disziplin. „A
> geschwächt“ ist nicht „B bewiesen“.

## Geltungsbereich

Diese Policy gilt für Claims mit `claim_kind: comparative_claim` oder
`burden_profile: comparative` und für jede Hypothesenbewertung, die
Modell-gegen-Modell-Sprache verwendet.

## Anforderungen

Für **jede** verglichene Hypothese ist zu dokumentieren:

1. **Unabhängige Bewertung**
   Jede Hypothese erhält eine eigene Bewertung mit eigenen
   `evidence_refs`, eigenen Defeatern und eigenen
   `required_chain`-Schritten, falls vorhanden.
2. **Positive Stützung**
   Für eine Hypothese darf nicht ausschließlich gelten „die Konkurrenz ist
   schwach“. Es muss mindestens eine positive Evidenz oder ein positiver
   Mechanismusbeleg vorliegen.
3. **Defeater pro Hypothese**
   Defeater werden pro Hypothese geführt. Ein Defeater gegen Hypothese A
   ist **kein** Defeater gegen Hypothese B.
4. **Bridge-Evidence**
   Der Übergang von „Modell A schwächt sich ab“ zu „Modell B ist
   wahrscheinlicher“ erfordert **explizite Bridge-Evidenz**: ein
   Beobachtungs-, Mechanismus- oder Daten-Bezug, der die Lücke füllt.
5. **No-Oracle**
   Die Vergleichsentscheidung darf nicht aus externer Autorität oder
   institutionellem Konsens deduziert werden, sondern muss
   evidenzstrukturiert geführt sein.
6. **No-Suspicion-to-Proof**
   Eine Hypothese erlangt keine starke Closure, indem ihr Verdacht durch
   Schwäche der Alternative gestützt wird.

## Anti-Muster

- *„Modell A erklärt B nicht vollständig → also war es Modell C.“*
  Falsch ohne positive Stützung von C.
- *„Es gibt keinen Konsens für A → A ist contradicted.“*
  Falsch; das ist eine Methodenlücke, kein Beweis.
- *„Alternative Erklärung existiert → starker Schluss möglich.“*
  Falsch; alternative Erklärungen senken Sicherheit, ersetzen aber keine
  positive Evidenz für irgendeine Hypothese.

## Erlaubte Muster

- *„Modell A hat einen ungeklärten Defeater an Schritt s. Modell B hat
  positive Stützung in Beobachtung o1 und o2. Bridge-Evidenz b1
  verbindet Modell B mit Beobachtung o3.“*
- *„Beide Modelle sind unvollständig; das Verdict bleibt `unresolved`,
  und der hoch-materiale Defeater wird in `model-defeaters.yml` geführt.“*

## Beziehung zu anderen Policies

- `docs/model-defeater-policy.md` definiert die Defeater-Mechanik.
- `docs/burden-layer-policy.md` trennt die Schichten, in denen Vergleiche
  geführt werden.
- `docs/no-oracle-policy.md` verhindert, dass externe Autorität den
  Vergleich vorentscheidet.
- `docs/verdict-discipline.md` regelt das resultierende `claim.status`.
