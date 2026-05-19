#!/usr/bin/env python3
"""Verify assessment.md prose is consistent with claims.yml status fields.

Detects when a claim is referenced in assessment.md and the surrounding
narrative uses certainty register incompatible with the claim's structured
status. See docs/status-prose-consistency.md.
"""

from __future__ import annotations

import pathlib
import re
import sys

import yaml

from case_compat import legacy_case_error

CASE_MARKERS = ("claims.yml", "evidence-relations.yml", "anomaly-ledger.yml", "investigation-integrity.yml")

# Phrases that are forbidden for a given status (cross-status global rules).
# These are the upgrade patterns from status-prose-consistency.md.
UPGRADE_PATTERNS = (
    r"\bis\s+the\s+case\s+that\b",
    r"\bwe\s+know\s+that\b",
    r"\bthe\s+truth\s+is\b",
    r"\bin\s+reality\b",
    r"\bas\s+a\s+matter\s+of\s+fact\b",
    r"\bist\s+der\s+fall,?\s+dass\b",
    r"\bwir\s+wissen,?\s+dass\b",
    r"\bdie\s+wahrheit\s+ist\b",
    r"\bin\s+wirklichkeit\b",
    r"\btats[aä]chlich\s+ist\b",
)

# Forbidden upgrade patterns when status is no_verdict_possible
NO_VERDICT_UPGRADE_PATTERNS = (
    r"\balthough\s+no\s+verdict\s+is\s+possible,?\s+the\s+most\s+likely\b",
    r"\bobwohl\s+kein\s+urteil\s+m[oö]glich\s+ist,?\s+deutet\b",
    r"\bdespite\s+the\s+lack\s+of\s+verdict,?\s+(?:we|the\s+evidence)\b",
    r"\bthe\s+most\s+plausible\s+(?:explanation|reading|interpretation)\s+(?:is|would\s+be)\b",
)

# Strong-register words that must NOT appear for a weak/speculative/unresolved claim
STRONG_REGISTER = re.compile(
    r"\b(established|etabliert|belegt|confirmed|best[aä]tigt|"
    r"strongly\s+supported|well[-\s]supported|stark\s+gest[uü]tzt|"
    r"proven|bewiesen|documented|dokumentiert|"
    r"settled|geklärt|geklart)\b",
    re.IGNORECASE,
)

WEAK_STATUSES = {"weak", "speculative", "unresolved", "no_verdict_possible"}
PLAUSIBLE_STATUSES = {"plausible"}
STRONG_STATUSES = {"strongly_supported", "established"}
NEGATIVE_STATUSES = {"contradicted"}

# Marker for human-readable status callout in markdown tables (e.g. "| c001 | weak |")
TABLE_ROW_PATTERN = re.compile(r"^\s*\|\s*(c\d{3,})\s*\|\s*([a-z_]+)\s*\|", re.IGNORECASE)
CLAIM_ID_PATTERN = re.compile(r"\bc\d{3,}\b")

STOPWORDS = {
    "the", "a", "an", "is", "was", "were", "are", "be", "of", "in", "to", "and", "or",
    "for", "by", "on", "with", "as", "at", "that", "this", "it", "its", "from", "into",
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer", "eines", "einem",
    "und", "oder", "in", "auf", "von", "mit", "zu", "bei", "für", "fur", "als", "ist",
    "war", "sind", "wird", "werden", "wurde", "wurden", "dem", "den", "an",
}


def safe_load_yaml(path: pathlib.Path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except Exception as exc:
        return None, str(exc)


def tokenize_statement(statement: str) -> list[str]:
    words = re.findall(r"[a-zäöüß0-9]+", statement.lower())
    return [w for w in words if w not in STOPWORDS and len(w) >= 4]


def split_sentences(text: str) -> list[tuple[int, str]]:
    """Return list of (start_index, sentence) tuples."""
    items: list[tuple[int, str]] = []
    pos = 0
    for match in re.finditer(r"[^.!?\n]+[.!?]?", text):
        s = match.group(0).strip()
        if s:
            items.append((match.start(), s))
        pos = match.end()
    return items


def is_in_block(text: str, char_index: int, start_marker: str, end_marker: str = "```") -> bool:
    """True if char_index is inside a fenced block of start_marker..end_marker."""
    inside = False
    for match in re.finditer(re.escape(start_marker) + r"|" + re.escape(end_marker), text):
        if match.start() > char_index:
            break
        if not inside:
            if match.group(0) == start_marker:
                inside = True
        else:
            if match.group(0) == end_marker:
                inside = False
    return inside


def is_in_blockquote(line: str) -> bool:
    return line.lstrip().startswith(">")


def is_in_table_status_cell(line: str, claim_id: str) -> bool:
    """True if line is a table row showing claim's status verbatim. Skipped for prose check."""
    m = TABLE_ROW_PATTERN.match(line)
    return bool(m and m.group(1).lower() == claim_id.lower())


def references_claim_in_sentence(sentence: str, claim_id: str, statement_tokens: list[str]) -> bool:
    """Heuristic: claim referenced if claim_id appears, or paraphrase tokens cluster."""
    if claim_id.lower() in sentence.lower():
        return True
    if not statement_tokens:
        return False
    sentence_tokens = tokenize_statement(sentence)
    if len(sentence_tokens) < 4:
        return False
    overlap = sum(1 for t in statement_tokens if t in sentence_tokens)
    return overlap >= 6


def get_window_sentences(sentences: list[tuple[int, str]], idx: int, window: int = 2) -> list[str]:
    start = max(0, idx - window)
    end = min(len(sentences), idx + window + 1)
    return [s for _, s in sentences[start:end]]


STICKY_WINDOW = 3  # sentences after an explicit reference also count


def check_prose_against_status(
    assessment_text: str,
    claim: dict,
) -> list[str]:
    """Return errors for a single claim."""
    errors: list[str] = []
    claim_id = claim.get("claim_id", "")
    status = claim.get("status", "")
    statement = claim.get("statement", "")
    if not claim_id or not status:
        return errors

    statement_tokens = tokenize_statement(statement)
    sentences = split_sentences(assessment_text)

    # Pre-compute sticky-reference windows: any sentence within
    # STICKY_WINDOW following a reference also counts as referencing,
    # unless we encounter (a) a different claim_id, or (b) a paragraph
    # break / heading, which reset the window.
    sticky_until = -1
    referenced: list[bool] = [False] * len(sentences)
    for idx, (char_start, sentence) in enumerate(sentences):
        # Detect resets:
        line_start = assessment_text.rfind("\n", 0, char_start) + 1
        line_end = assessment_text.find("\n", char_start)
        if line_end == -1:
            line_end = len(assessment_text)
        line = assessment_text[line_start:line_end]
        other_ids = [m for m in CLAIM_ID_PATTERN.findall(sentence) if m.lower() != claim_id.lower()]
        if other_ids:
            sticky_until = -1  # reset on different claim_id
        if line.lstrip().startswith("#") or line.strip() == "":
            sticky_until = -1  # reset on heading/blank line
        if references_claim_in_sentence(sentence, claim_id, statement_tokens):
            sticky_until = idx + STICKY_WINDOW
        if idx <= sticky_until and not other_ids:
            referenced[idx] = True

    for idx, (char_start, sentence) in enumerate(sentences):
        # Skip table status cell lines
        line_start = assessment_text.rfind("\n", 0, char_start) + 1
        line_end = assessment_text.find("\n", char_start)
        if line_end == -1:
            line_end = len(assessment_text)
        line = assessment_text[line_start:line_end]
        if is_in_table_status_cell(line, claim_id):
            continue
        if is_in_blockquote(line):
            continue
        if is_in_block(assessment_text, char_start, "```steelman"):
            continue

        if not referenced[idx]:
            continue

        # Check global upgrade patterns
        for pattern in UPGRADE_PATTERNS:
            for match in re.finditer(pattern, sentence, flags=re.IGNORECASE):
                if status not in {"established"}:
                    errors.append(
                        f"  claim {claim_id} (status={status}): prose uses upgrade phrase '{match.group(0)}' which implies factual closure; line: '{sentence[:120]}'"
                    )

        # Check no_verdict_possible specific upgrades
        if status == "no_verdict_possible":
            for pattern in NO_VERDICT_UPGRADE_PATTERNS:
                if re.search(pattern, sentence, flags=re.IGNORECASE):
                    errors.append(
                        f"  claim {claim_id} (status=no_verdict_possible): prose smuggles a verdict via '{pattern}'; line: '{sentence[:120]}'"
                    )

        # Check strong register on weak/speculative/unresolved/no_verdict
        if status in WEAK_STATUSES:
            for match in STRONG_REGISTER.finditer(sentence):
                # Exclude "well-supported counterhypothesis" by checking a small window
                # for negations within the same sentence
                snippet = sentence[max(0, match.start() - 25):match.end() + 25].lower()
                if any(neg in snippet for neg in ("not ", "kein ", "keine ", "nicht ", "no ")):
                    continue
                # Exclude when "counter" appears in same sentence (claim's counterhypothesis being strong is allowed)
                if "counter" in sentence.lower() or "gegenhypothese" in sentence.lower():
                    continue
                errors.append(
                    f"  claim {claim_id} (status={status}): prose uses strong register '{match.group(0)}' incompatible with the weak/speculative/unresolved/no_verdict_possible status; line: '{sentence[:120]}'"
                )

        # contradicted status: must reference direct exclusion in same sentence/window
        if status == "contradicted":
            window = " ".join(get_window_sentences(sentences, idx, window=1)).lower()
            exclusion_terms = (
                "rules out", "rule out", "excludes", "excluded",
                "physically impossible", "temporally impossible",
                "schliesst aus", "schließt aus", "physikalisch unmöglich",
                "zeitlich unmöglich", "direct exclusion", "direkte exklusion",
                "incompatibility", "inkompatibilität",
            )
            if not any(term in window for term in exclusion_terms):
                errors.append(
                    f"  claim {claim_id} (status=contradicted): prose discusses claim without reference to a direct exclusion basis in the ±1 sentence window; line: '{sentence[:120]}'"
                )

    return errors


def validate_case(case_dir: pathlib.Path) -> list[str]:
    errors: list[str] = []
    legacy_error = legacy_case_error(case_dir)
    if legacy_error:
        return [legacy_error]

    claims_path = case_dir / "claims.yml"
    assessment_path = case_dir / "assessment.md"
    if not claims_path.exists() or not assessment_path.exists():
        return []

    claims_data, err = safe_load_yaml(claims_path)
    if err:
        return [f"Could not parse claims.yml: {err}"]
    if not isinstance(claims_data, dict):
        return ["claims.yml must contain a YAML object."]

    try:
        assessment_text = assessment_path.read_text(encoding="utf-8")
    except Exception as exc:
        return [f"Could not read assessment.md: {exc}"]

    for claim in claims_data.get("claims", []):
        if not isinstance(claim, dict):
            continue
        errors.extend(check_prose_against_status(assessment_text, claim))

    return errors


def is_case_dir(path: pathlib.Path) -> bool:
    return any((path / marker).exists() for marker in CASE_MARKERS)


def discover_case_dirs(root: pathlib.Path) -> list[pathlib.Path]:
    candidate_dirs = {root}
    for marker in CASE_MARKERS:
        candidate_dirs.update(path.parent for path in root.rglob(marker))
    return sorted(d for d in candidate_dirs if d.is_dir() and "_template" not in d.parts and is_case_dir(d))


def main(cases_root: str) -> int:
    root = pathlib.Path(cases_root)
    case_dirs = discover_case_dirs(root)
    if not case_dirs:
        print(f"No case directories found under {root}")
        return 0

    total_errors = 0
    for case_dir in case_dirs:
        errors = validate_case(case_dir)
        if errors:
            print(f"FAIL {case_dir}:")
            for error in errors:
                print(f"  {error}")
            total_errors += len(errors)
        else:
            print(f"OK   {case_dir}")

    if total_errors:
        print(f"\n{total_errors} status/prose consistency error(s) found.")
        return 1
    print("\nAll status/prose consistency checks valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
