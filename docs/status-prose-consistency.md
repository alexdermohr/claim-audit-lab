# Status / Prose Consistency Discipline

## Principle

The structured `status` field in `claims.yml` is the binding verdict. The narrative
in `assessment.md` is the human-facing summary. If they diverge, the narrative
silently overrides the schema — and the schema's enforcement collapses.

Agents trained on majority-narrative corpora reliably write prose that **upgrades**
a `weak` or `plausible` or `no_verdict_possible` claim to sound `established`. The
schema still says `weak`; the validator still passes; the reader sees certainty.

This policy closes the loop: prose mentions of a claim must use language that is
compatible with the claim's structured `status`. The validator
`scripts/validate_status_prose_consistency.py` enforces this.

## Compatibility table

For each `status`, the prose mentioning that claim's `claim_id` (e.g. `c001`) or
its `statement` may use **only** language from the allowed register:

| status | allowed register in prose |
|---|---|
| `established` | strong factual register: "established", "documented", "etabliert", "belegt" |
| `strongly_supported` | strong-but-bounded: "strongly supported", "well-supported", "stark gestützt" |
| `plausible` | conditional: "plausible", "consistent with", "plausibel", "vereinbar mit" |
| `weak` | hedged: "weak", "underdetermined", "schwach", "unzureichend gestützt" |
| `speculative` | speculative-marked: "speculative", "hypothetical", "spekulativ", "hypothetisch" |
| `contradicted` | requires direct exclusion language; **must** cite the `direct_incompatibility_basis` |
| `unresolved` | open: "unresolved", "open", "ungeklärt", "offen" |
| `no_verdict_possible` | non-verdict: "no verdict possible", "untestable with current evidence", "kein Urteil möglich" |

## Forbidden upgrade patterns (regardless of register)

These cross-cutting patterns are forbidden when discussing any claim with status
below `established`:

- "is the case that X" / "ist der Fall, dass X" — implies factual closure
- "we know that X" / "wir wissen, dass X" — implies certainty
- "the truth is X" / "die Wahrheit ist X" — invokes the no-oracle principle
- "in reality X" / "in Wirklichkeit X" — invokes truth authority
- "as a matter of fact X" / "tatsächlich ist X" (in conclusion register)

For claims with status `no_verdict_possible`, the prose may **not** contain
sentences that draw inferences as if a verdict existed. Specifically:
- "Although no verdict is possible, the most likely explanation is X" — banned
- "Obwohl kein Urteil möglich ist, deutet alles auf X hin" — banned

`no_verdict_possible` means: no verdict. It does not mean "tentative verdict in
favour of the most-likely-sounding option."

## How the validator works

The validator parses each `assessment.md`, locates references to claims (by `claim_id`
like `c001`, `c023`, or by close paraphrase of the claim's `statement`), and checks
the surrounding sentence(s) against the allowed register and forbidden patterns for
that claim's structured `status`.

A reference is detected when:
- a token matches `c\d{3,}` (claim ID), OR
- a sentence contains ≥ 6 consecutive lowercased non-stopwords from the claim's
  `statement` (paraphrase detection), OR
- the claim is mentioned in a table row in `assessment.md` (matched by `claim_id`).

The validator considers a window of ±2 sentences around the reference.

## Exceptions

The validator skips:
- Verbatim quotes of the structured `status` (e.g. a table cell saying `weak`)
- Blockquoted user-question text
- Counterhypothesis reconstructions inside ```` ```steelman ```` blocks
- The mandatory oracle disclaimer

## Why this matters

If an agent writes a `weak` verdict in `claims.yml` but writes an `established`-style
narrative in `assessment.md`, a human reader experiences the case as "the framework
agrees with the narrative", and the structured caution is lost. The verdict caps,
counterhypothesis requirements, and red-team gates all become decorative.

This validator restores the binding character of the structured `status` by
requiring prose to be consistent with it.
