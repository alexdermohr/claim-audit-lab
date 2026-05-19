#!/usr/bin/env python3
"""Block forbidden language in agent prose.

Scans assessment.md, redteam.md, question.md agent-framing sections, and
answer-receipt.yml free-text fields for phrases listed in
docs/forbidden-language.md. Skips quoted material, source-position
descriptions, and fenced code blocks (including steelman blocks).

See: docs/forbidden-language.md
"""

from __future__ import annotations

import pathlib
import re
import sys

import yaml

from case_compat import legacy_case_error

CASE_MARKERS = ("claims.yml", "evidence-relations.yml", "anomaly-ledger.yml", "investigation-integrity.yml")

# Category A: false-closure phrases
FALSE_CLOSURE_PATTERNS = (
    r"\bdefinitively\b",
    r"\bdefinitely\b",
    r"\bwithout\s+(?:any\s+)?doubt\b",
    r"\bno\s+doubt\b",
    r"\bbeyond\s+(?:reasonable\s+)?doubt\b",
    r"\bsettled\s+science\b",
    r"\bscientific\s+consensus\b",
    r"\bthe\s+consensus\s+is\b",
    r"\bobviously\b",
    r"\bclearly\s+demonstrates?\b",
    r"\bleaves?\s+no\s+room\b",
    r"\bproves?\s+that\b",
    r"\b(?:is\s+|was\s+)?proven\b",
    r"\bfact\s+is\s+that\b",
    r"\bas\s+everyone\s+knows\b",
    r"\bwell[-\s]established\s+fact\b",
    r"\bindisputable\b",
    r"\bzweifelsfrei\b",
    r"\bohne\s+(?:jeden\s+|jeglichen\s+)?zweifel\b",
    r"\bunbestreitbar\b",
    r"\bunstrittig\b",
    r"\bwissenschaftliche[rsnm]?\s+konsens\b",
    r"\bdie\s+wissenschaft\s+ist\s+sich\s+einig\b",
    r"\bselbstverst[aä]ndlich\b",
    r"\boffensichtlich\b",
    r"\bbeweist,?\s+dass\b",
    r"\bist\s+erwiesen\b",
    r"\btatsache\s+ist\b",
    r"\bwie\s+jeder\s+wei[sß]\b",
    r"\ballgemein\s+anerkannt\b",
)

# Category B: dismissal phrases
DISMISSAL_PATTERNS = (
    r"\bconspiracy\s+theor(?:y|ies|ist)\b",
    r"\btin[-\s]?foil\b",
    r"\bdebunked\b",
    r"\bfringe\s+(?:theory|view|hypothesis)\b",
    r"\bdiscredited\b",
    r"\b(?:mis|dis)information\b",
    r"\bverschw[oö]rungstheor(?:ie|ien|etiker)\b",
    r"\bl[aä]ngst\s+widerlegt\b",
    r"\bwiderlegt\b",
    r"\brandmeinung\b",
    r"\bau[sß]enseitermeinung\b",
    r"\bdiskreditiert\b",
    r"\b(?:falsch|des)information\b",
)

# Category C: authority laundering
AUTHORITY_LAUNDERING_PATTERNS = (
    r"\bexperts\s+agree\b",
    r"\bscientists\s+say\b",
    r"\baccording\s+to\s+the\s+consensus\b",
    r"\bofficials\s+confirm(?:ed)?\b",
    r"\bauthorities\s+confirm(?:ed)?\b",
    r"\btrusted\s+sources\b",
    r"\breliable\s+sources\b",
    r"\bmainstream\s+view\s+holds\b",
    r"\bmainstream\s+science\b",
    r"\bexperten\s+sind\s+sich\s+einig\b",
    r"\bwissenschaftler\s+sagen\b",
    r"\boffiziell\s+best[aä]tigt\b",
    r"\bbeh[oö]rden\s+best[aä]tigen\b",
    r"\bseri[oö]se\s+quellen\b",
    r"\bvertrauensw[uü]rdige\s+quellen\b",
    r"\bder\s+wissenschaftliche\s+mainstream\b",
)

# Category D: smoothing phrases
SMOOTHING_PATTERNS = (
    r"\bwhile\s+some\s+disagree,?\s+overall\b",
    r"\bbroadly\s+speaking\b",
    r"\bin\s+general\s+it\s+is\s+fair\s+to\s+say\b",
    r"\bthe\s+underlying\s+point\s+stands\b",
    r"\bregardless\s+of\s+minor\s+(?:disputes|disagreements)\b",
    r"\btrotz\s+kleinerer\s+abweichungen\b",
    r"\bim\s+gro[sß]en\s+und\s+ganzen\b",
    r"\bim\s+wesentlichen\b",
    r"\bder\s+kern\s+der\s+aussage\s+bleibt\b",
    r"\bungeachtet\s+einzelner\s+stimmen\b",
)

# Category E: refusal-as-neutrality
REFUSAL_PATTERNS = (
    r"\bi\s+(?:cannot|can[' ]?t|won[' ]?t)\s+(?:evaluate|assess|judge)\b",
    r"\bthis\s+is\s+a\s+sensitive\s+topic\b",
    r"\bnot\s+appropriate\s+to\s+assess\b",
    r"\bboth\s+sides\s+have\s+valid\s+points\b",
    r"\bkann\s+ich\s+nicht\s+bewerten\b",
    r"\bein\s+sensibles\s+thema,?\s+daher\b",
    r"\bes\s+w[aä]re\s+unangemessen,?\s+dies\s+zu\s+beurteilen\b",
    r"\bbeide\s+seiten\s+haben\s+gute\s+argumente\b",
    r"\bzu\s+politisch,?\s+um\s+sie\s+zu\s+beantworten\b",
)

CATEGORIES = (
    ("false_closure", FALSE_CLOSURE_PATTERNS),
    ("dismissal", DISMISSAL_PATTERNS),
    ("authority_laundering", AUTHORITY_LAUNDERING_PATTERNS),
    ("smoothing", SMOOTHING_PATTERNS),
    ("refusal_as_neutrality", REFUSAL_PATTERNS),
)

# Allowed-context markers that cause the validator to skip lines.
# Lines that START WITH one of these prefixes are entirely skipped.
ALLOWED_CONTEXT_LINE_PREFIXES = (
    "> ",
    "Quoted:",
    "Source position:",
    "Quelle behauptet:",
    "Position summary:",
    "Banned phrase example:",
    "Beispiel (verboten):",
)

# Inline markers: if a line CONTAINS one of these (anywhere), the banned-phrase
# scan skips that line, because the line is explicitly citing source-position
# language for audit. The presence of these markers must be accompanied by
# quotation marks around the banned phrase to count.
ALLOWED_INLINE_CITATION_MARKERS = (
    "Source position:",
    "Source position from",
    "Quoted from",
    "Quoted source position",
    "Quoted verbatim",
    "Quelle behauptet:",
    "Audit-Subjekt-Sprache:",
    "Audit-Subjekt-Sprache from",
    "Banned phrase example:",
    "Beispiel (verboten):",
)

ALLOWED_CONTEXT_YAML_KEYS = (
    "quote",
    "position_summary",
    "source_position",
    "banned_phrase_example",
    "phrase",  # in banned_phrases_self_scan.hits
)


def safe_load_yaml(path: pathlib.Path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f), None
    except Exception as exc:
        return None, str(exc)


def is_in_meta_doc(path: pathlib.Path) -> bool:
    """The banned-language doc itself and agent-contract.md contain examples; skip."""
    name = path.name
    return name in ("forbidden-language.md", "agent-contract.md", "refusal-discipline.md")


def line_is_allowed_context(line: str) -> bool:
    stripped = line.lstrip()
    if any(stripped.startswith(prefix) for prefix in ALLOWED_CONTEXT_LINE_PREFIXES):
        return True
    # Inline citation marker present anywhere in the line
    if any(marker in line for marker in ALLOWED_INLINE_CITATION_MARKERS):
        # Require at least one quotation mark on the same line; otherwise the
        # marker is not a real citation, just a name-drop.
        if '"' in line or "'" in line or "„" in line or "‚" in line or "»" in line:
            return True
    return False


def _split_question_user_and_agent_sections(text: str) -> tuple[str, str, int]:
    """Return (user_question_section, agent_framing_section, agent_start_line_offset)."""
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        lower = line.strip().lower()
        if lower.startswith("## scope") or lower.startswith("## method") or lower.startswith("## why"):
            return ("\n".join(lines[:idx]), "\n".join(lines[idx:]), idx)
    return (text, "", 0)


def scan_markdown_text(path: pathlib.Path, *, scan_question_agent_framing_only: bool = False) -> list[tuple[int, str, str, str]]:
    """Scan a markdown file. Returns list of (line_no, category, phrase, line_text)."""
    if not path.exists():
        return []
    if is_in_meta_doc(path):
        return []
    full_text = path.read_text(encoding="utf-8")
    line_offset = 0
    text = full_text
    if scan_question_agent_framing_only:
        _, agent_text, start_line = _split_question_user_and_agent_sections(full_text)
        if not agent_text.strip():
            return []
        text = agent_text
        line_offset = start_line
    lines = text.splitlines()
    hits: list[tuple[int, str, str, str]] = []
    inside_code_block = False
    inside_steelman = False
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```steelman"):
            inside_code_block = True
            inside_steelman = True
            continue
        if stripped.startswith("```"):
            inside_code_block = not inside_code_block
            if not inside_code_block:
                inside_steelman = False
            continue
        if inside_steelman:
            continue
        if inside_code_block:
            continue
        if line_is_allowed_context(line):
            continue
        lowered = line.lower()
        for category, patterns in CATEGORIES:
            for pattern in patterns:
                for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
                    hits.append((idx + 1 + line_offset, category, match.group(0), line.strip()))
    return hits


def scan_receipt_yaml(path: pathlib.Path) -> list[tuple[str, str, str, str]]:
    """Scan an answer-receipt.yml. Returns list of (field_path, category, phrase, text_snippet)."""
    if not path.exists():
        return []
    data, err = safe_load_yaml(path)
    if err or not isinstance(data, dict):
        return []
    scannable_fields = (
        "answer_summary",
        "final_uncertainty_statement",
        "what_would_change_assessment",
        "notes",
    )
    hits: list[tuple[str, str, str, str]] = []
    for field in scannable_fields:
        text = data.get(field)
        if not isinstance(text, str):
            continue
        lowered = text.lower()
        for category, patterns in CATEGORIES:
            for pattern in patterns:
                for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
                    hits.append((field, category, match.group(0), text[:120]))

    # Verify banned_phrases_self_scan honesty:
    self_scan = data.get("banned_phrases_self_scan", {})
    declared_hits = self_scan.get("hits", []) if isinstance(self_scan, dict) else []
    declared_phrases = {h.get("phrase", "").lower() for h in declared_hits if isinstance(h, dict)}
    answer_summary = data.get("answer_summary", "") or ""
    answer_lowered = answer_summary.lower()
    for category, patterns in CATEGORIES:
        for pattern in patterns:
            for match in re.finditer(pattern, answer_lowered, flags=re.IGNORECASE):
                phrase = match.group(0).lower()
                if phrase not in declared_phrases:
                    hits.append((
                        "banned_phrases_self_scan",
                        category,
                        phrase,
                        f"Phrase appears in answer_summary but is not declared in self_scan.hits",
                    ))
    return hits


def scan_case(case_dir: pathlib.Path) -> list[str]:
    errors: list[str] = []
    legacy_error = legacy_case_error(case_dir)
    if legacy_error:
        return [legacy_error]

    for filename in ("assessment.md", "redteam.md"):
        hits = scan_markdown_text(case_dir / filename)
        for line_no, category, phrase, text in hits:
            errors.append(
                f"{filename}:{line_no} category={category} phrase='{phrase}' line='{text[:100]}'"
            )

    question_path = case_dir / "question.md"
    question_hits = scan_markdown_text(question_path, scan_question_agent_framing_only=True)
    for line_no, category, phrase, text in question_hits:
        errors.append(
            f"question.md:{line_no} category={category} phrase='{phrase}' line='{text[:100]}'"
        )

    receipt_hits = scan_receipt_yaml(case_dir / "answer-receipt.yml")
    for field, category, phrase, text in receipt_hits:
        errors.append(
            f"answer-receipt.yml field={field} category={category} phrase='{phrase}' snippet='{text[:100]}'"
        )

    # Scan free-form answer files (answers/*.md if present)
    answers_dir = case_dir / "answers"
    if answers_dir.is_dir():
        for answer_path in sorted(answers_dir.glob("*.md")):
            hits = scan_markdown_text(answer_path)
            for line_no, category, phrase, text in hits:
                errors.append(
                    f"answers/{answer_path.name}:{line_no} category={category} phrase='{phrase}' line='{text[:100]}'"
                )

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
        errors = scan_case(case_dir)
        if errors:
            print(f"FAIL {case_dir}:")
            for error in errors:
                print(f"  {error}")
            total_errors += len(errors)
        else:
            print(f"OK   {case_dir}")

    if total_errors:
        print(f"\n{total_errors} forbidden-language hit(s) found.")
        return 1
    print("\nAll forbidden-language checks valid.")
    return 0


if __name__ == "__main__":
    cases_dir = sys.argv[1] if len(sys.argv) > 1 else "cases"
    sys.exit(main(cases_dir))
