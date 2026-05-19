# Forbidden Language Discipline

## Principle

Bias is not only smuggled through verdicts. It is smuggled through **language**.

Agents trained on majority-narrative corpora reliably reproduce a small set of certainty
phrases, dismissal phrases, and authority-laundering phrases. These phrases functionally
upgrade weak verdicts to strong ones, smooth contradictions, and convert source prestige
into truth — without ever changing the structured `status` field.

This policy lists banned phrases that may **not** appear in agent prose
(`assessment.md`, answer text, redteam.md, hypothesis prose) when used to express the
agent's own evaluation. The same phrases may appear in **quoted material**, in
**descriptions of source positions**, or in **counterhypothesis reconstructions**, as long
as the surrounding context clearly attributes them to a source and not to the agent.

`scripts/validate_forbidden_language.py` enforces this list. A hit is a hard fail.

## Scope

The validator scans these files in every case:
- `assessment.md`
- `redteam.md`
- `question.md` (only the agent's framing section, not the user's question text)
- `answer-receipt.yml` free-text fields (`answer_summary`, `final_uncertainty_statement`,
  `what_would_change_assessment`, `notes`)

The validator skips Markdown blockquotes (`>`), fenced code blocks (```), and lines
prefixed with `Quoted:` or `Source position:` — these are treated as cited material.

## Banned categories

### Category A: false-closure phrases
These phrases imply a settled verdict where no `established` status is present.

English:
- "definitely", "definitively", "without doubt", "no doubt", "beyond doubt"
- "settled science", "scientific consensus", "the consensus is"
- "obviously", "clearly demonstrates", "leaves no room"
- "proves that", "proven", "fact is that"
- "as everyone knows", "well-established fact", "indisputable"

German:
- "zweifelsfrei", "ohne Zweifel", "unbestreitbar", "unstrittig"
- "wissenschaftlicher Konsens", "die Wissenschaft ist sich einig"
- "selbstverständlich", "offensichtlich"
- "beweist, dass", "ist erwiesen", "Tatsache ist"
- "wie jeder weiß", "allgemein anerkannt"

### Category B: dismissal phrases
These phrases pre-discredit a hypothesis without engaging its strongest form (steelman policy).

English:
- "conspiracy theory", "conspiracy theorist", "tin-foil"
- "debunked" (when used as label, not as outcome of a documented test)
- "fringe theory", "fringe view"
- "discredited" (when used as label, without citing the test that discredited it)
- "misinformation", "disinformation" (when used as label, not as documented finding)

German:
- "Verschwörungstheorie", "Verschwörungstheoretiker"
- "längst widerlegt", "widerlegt" (als Label, nicht als Testresultat)
- "Randmeinung", "Außenseitermeinung"
- "diskreditiert" (als Label)
- "Falschinformation", "Desinformation" (als Label, nicht als belegter Befund)

### Category C: authority laundering
These phrases convert source prestige into truth (System-Invariante #4: Quelle ≠ Beweis).

English:
- "experts agree", "scientists say", "according to the consensus"
- "officials confirm", "authorities confirmed"
- "trusted sources", "reliable sources" (when used to imply truth, not classification)
- "mainstream view holds", "mainstream science"

German:
- "Experten sind sich einig", "Wissenschaftler sagen"
- "offiziell bestätigt", "Behörden bestätigen"
- "seriöse Quellen", "vertrauenswürdige Quellen" (als Wahrheitsmarker)
- "der wissenschaftliche Mainstream"

### Category D: smoothing phrases
These phrases glue contradictions shut (System-Invariante #8: Widerspruch darf nicht
geglättet werden).

English:
- "while some disagree, overall"
- "broadly speaking", "in general it is fair to say"
- "the underlying point stands"
- "regardless of minor disputes"

German:
- "trotz kleinerer Abweichungen"
- "im Großen und Ganzen", "im Wesentlichen"
- "der Kern der Aussage bleibt"
- "ungeachtet einzelner Stimmen"

### Category E: refusal-as-neutrality
These phrases dress refusal up as balance (System-Invariante #6: Verweigerung ≠
Neutralität).

English:
- "I cannot evaluate"
- "this is a sensitive topic and I won't"
- "it is not appropriate to assess"
- "both sides have valid points" (without separate evaluation of each)

German:
- "kann ich nicht bewerten"
- "ein sensibles Thema, daher"
- "es wäre unangemessen, dies zu beurteilen"
- "beide Seiten haben gute Argumente" (ohne separate Auswertung)

## Allowed usage contexts

The same phrases are **allowed** if they appear in:

1. **Quoted material**: prefixed by `> ` (Markdown blockquote) or contained in
   `quote: "..."` YAML fields.
2. **Source-position descriptions**: lines prefixed by `Source position:`,
   `Quelle behauptet:`, or contained in a `position_summary:` YAML field.
3. **Steelman reconstructions**: lines inside a fenced block starting with
   ```` ```steelman ```` and ending with ```` ``` ````.
4. **Banned-language demonstrations** inside this policy file or
   `docs/agent-contract.md`.

The validator detects these markers and skips them.

## Why this is enforceable

Agents may believe they are being neutral when they use Category C phrases. The
validator does not care about belief. It cares about the output token sequence. If a
banned phrase appears outside an allowed context, the case fails to validate. The
agent cannot ship its answer to the repo. There is no negotiation with the regex.

## Rationale

Every phrase in the banned list maps to at least one System-Invariante violation or
one blocking gate violation. The list is not stylistic preference; it is the
verbal projection of the discipline that the structured schemas already encode.

If a banned phrase is the only way to express a true point, that is a signal that
the framework lacks a verdict for that point — not that the framework should be
bypassed. File an issue to extend the verdict vocabulary or the policy.
