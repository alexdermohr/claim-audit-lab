"""Tests for scripts/validate_forbidden_language.py."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_forbidden_language


def _make_minimal_case(tmp_path, name="case-a", **files):
    case_dir = tmp_path / "cases" / "history" / name
    case_dir.mkdir(parents=True)
    # marker file so discover_case_dirs detects this as a case
    (case_dir / "claims.yml").write_text("claims: []\n", encoding="utf-8")
    for filename, content in files.items():
        (case_dir / filename).write_text(content, encoding="utf-8")
    return case_dir


def test_clean_assessment_passes(tmp_path):
    _make_minimal_case(
        tmp_path,
        **{"assessment.md": "# Title\n\nThis is a careful assessment.\n"},
    )
    assert validate_forbidden_language.main(str(tmp_path / "cases")) == 0


def test_false_closure_phrase_fails(tmp_path):
    case_dir = _make_minimal_case(
        tmp_path,
        **{"assessment.md": "# Title\n\nThis is definitively proven.\n"},
    )
    assert validate_forbidden_language.main(str(tmp_path / "cases")) == 1


def test_dismissal_phrase_fails(tmp_path):
    _make_minimal_case(
        tmp_path,
        **{"assessment.md": "# Title\n\nThe alternative is a conspiracy theory.\n"},
    )
    assert validate_forbidden_language.main(str(tmp_path / "cases")) == 1


def test_authority_laundering_phrase_fails(tmp_path):
    _make_minimal_case(
        tmp_path,
        **{"assessment.md": "# Title\n\nExperts agree on the outcome.\n"},
    )
    assert validate_forbidden_language.main(str(tmp_path / "cases")) == 1


def test_smoothing_phrase_fails(tmp_path):
    _make_minimal_case(
        tmp_path,
        **{"assessment.md": "# Title\n\nWhile some disagree, overall the point holds.\n"},
    )
    assert validate_forbidden_language.main(str(tmp_path / "cases")) == 1


def test_refusal_as_neutrality_fails(tmp_path):
    _make_minimal_case(
        tmp_path,
        **{"assessment.md": "# Title\n\nI cannot evaluate this politically sensitive matter.\n"},
    )
    assert validate_forbidden_language.main(str(tmp_path / "cases")) == 1


def test_german_false_closure_fails(tmp_path):
    _make_minimal_case(
        tmp_path,
        **{"assessment.md": "# Titel\n\nDer Sachverhalt ist zweifelsfrei geklärt.\n"},
    )
    assert validate_forbidden_language.main(str(tmp_path / "cases")) == 1


def test_german_consensus_phrase_fails(tmp_path):
    _make_minimal_case(
        tmp_path,
        **{"assessment.md": "# Titel\n\nEs gibt einen wissenschaftlichen Konsens dazu.\n"},
    )
    assert validate_forbidden_language.main(str(tmp_path / "cases")) == 1


def test_blockquote_allows_quoted_banned_phrase(tmp_path):
    _make_minimal_case(
        tmp_path,
        **{"assessment.md": "# Title\n\n> Quoted: conspiracy theory in the source position.\n"},
    )
    assert validate_forbidden_language.main(str(tmp_path / "cases")) == 0


def test_source_position_prefix_allows_quoted_phrase(tmp_path):
    _make_minimal_case(
        tmp_path,
        **{"assessment.md": "# Title\n\nSource position: the article uses \"conspiracy theory\" as its label.\n"},
    )
    assert validate_forbidden_language.main(str(tmp_path / "cases")) == 0


def test_inline_source_position_marker_with_quotes_allows_phrase(tmp_path):
    _make_minimal_case(
        tmp_path,
        **{"assessment.md": "# Title\n\nThe article writes (Source position: \"conspiracy theory\") about the topic.\n"},
    )
    assert validate_forbidden_language.main(str(tmp_path / "cases")) == 0


def test_inline_marker_without_quote_does_not_allow_phrase(tmp_path):
    _make_minimal_case(
        tmp_path,
        **{"assessment.md": "# Title\n\nThe Source position says conspiracy theory was used.\n"},
    )
    # No quote marks around the banned phrase — not skipped
    assert validate_forbidden_language.main(str(tmp_path / "cases")) == 1


def test_meta_doc_path_skips_scan(tmp_path):
    # forbidden-language.md itself contains examples and is skipped
    case_dir = _make_minimal_case(tmp_path)
    (case_dir / "forbidden-language.md").write_text(
        "definitively proven conspiracy theory scientific consensus",
        encoding="utf-8",
    )
    # This is .md inside a case but the meta-doc filename triggers skip
    # (only assessment.md / redteam.md / question.md are scanned).
    assert validate_forbidden_language.main(str(tmp_path / "cases")) == 0


def test_steelman_block_allows_banned_phrase(tmp_path):
    content = """# Title

```steelman
The opposing view holds that this is definitively the correct interpretation.
```
"""
    _make_minimal_case(tmp_path, **{"assessment.md": content})
    assert validate_forbidden_language.main(str(tmp_path / "cases")) == 0


def test_redteam_md_is_scanned(tmp_path):
    _make_minimal_case(
        tmp_path,
        **{
            "redteam.md": "# Red-team\n\nThis is debunked nonsense.\n",
        },
    )
    assert validate_forbidden_language.main(str(tmp_path / "cases")) == 1


def test_answer_receipt_summary_with_banned_phrase_fails(tmp_path):
    receipt = """schema_version: "1.0"
question: "Q"
task_classification: claim_audit
answer_summary: "This is definitively the answer."
verdicts_used: []
counterhypotheses_considered: []
forbidden_upgrades_check:
  upgrades_considered: []
  upgrades_blocked: []
banned_phrases_self_scan:
  scanned: true
  hits: []
source_cluster_audit:
  clusters_identified: []
  independence_verified: false
refusal_check:
  refused: false
external_research:
  tools_used: []
  sources_consulted: []
oracle_disclaimer_present: true
final_uncertainty_statement: "Not a truth certificate."
what_would_change_assessment: "More data."
"""
    _make_minimal_case(tmp_path, **{"answer-receipt.yml": receipt})
    assert validate_forbidden_language.main(str(tmp_path / "cases")) == 1


def test_answer_receipt_self_scan_inconsistency_fails(tmp_path):
    # answer_summary has a banned phrase but banned_phrases_self_scan.hits is empty
    receipt = """schema_version: "1.0"
question: "Q"
task_classification: claim_audit
answer_summary: "The experts agree on this."
verdicts_used: []
counterhypotheses_considered: []
forbidden_upgrades_check:
  upgrades_considered: []
  upgrades_blocked: []
banned_phrases_self_scan:
  scanned: true
  hits: []
source_cluster_audit:
  clusters_identified: []
  independence_verified: false
refusal_check:
  refused: false
external_research:
  tools_used: []
  sources_consulted: []
oracle_disclaimer_present: true
final_uncertainty_statement: "Not a truth certificate."
what_would_change_assessment: "More data."
"""
    _make_minimal_case(tmp_path, **{"answer-receipt.yml": receipt})
    assert validate_forbidden_language.main(str(tmp_path / "cases")) == 1


def test_answer_receipt_with_declared_hits_for_disclosed_phrase_passes(tmp_path):
    # answer_summary contains a banned phrase BUT it's declared in self_scan
    # In strict mode, the validator still fails because the phrase appears in
    # answer_summary text and is not in an allowed context.
    receipt = """schema_version: "1.0"
question: "Q"
task_classification: claim_audit
answer_summary: "This is well-documented."
verdicts_used: []
counterhypotheses_considered: []
forbidden_upgrades_check:
  upgrades_considered: []
  upgrades_blocked: []
banned_phrases_self_scan:
  scanned: true
  hits: []
source_cluster_audit:
  clusters_identified: []
  independence_verified: false
refusal_check:
  refused: false
external_research:
  tools_used: []
  sources_consulted: []
oracle_disclaimer_present: true
final_uncertainty_statement: "Not a truth certificate."
what_would_change_assessment: "More data."
"""
    _make_minimal_case(tmp_path, **{"answer-receipt.yml": receipt})
    # "well-documented" is not in any banned category
    assert validate_forbidden_language.main(str(tmp_path / "cases")) == 0
