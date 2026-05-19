"""Tests for scripts/validate_status_prose_consistency.py."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_status_prose_consistency


def _make_case(tmp_path, claims_yaml, assessment_md, name="case-a"):
    case_dir = tmp_path / "cases" / "history" / name
    case_dir.mkdir(parents=True)
    (case_dir / "claims.yml").write_text(claims_yaml, encoding="utf-8")
    (case_dir / "assessment.md").write_text(assessment_md, encoding="utf-8")
    return case_dir


WEAK_CLAIM = """schema_version: "1.0"
claims:
  - schema_version: "1.0"
    claim_id: "c001"
    claim_type: "factual_event_claim"
    statement: "The mainstream evaluation was independent of cluster effects in the documented channels."
    status: "weak"
    uncertainty:
      score: 0.6
      causes: ["pauschale Aussage"]
    interpolation:
      score: 0.5
      assumptions: ["A"]
"""

ESTABLISHED_CLAIM = """schema_version: "1.0"
claims:
  - schema_version: "1.0"
    claim_id: "c001"
    claim_type: "factual_event_claim"
    statement: "The Lancet authors had documented institutional ties."
    status: "established"
    evidence_refs: ["e001"]
    source_refs: ["s001"]
    uncertainty:
      score: 0.1
      causes: ["A"]
    interpolation:
      score: 0.05
      assumptions: ["A"]
"""


def test_weak_claim_with_hedged_prose_passes(tmp_path):
    assessment = """# Title

The c001 claim is weak; the evaluation is underdetermined by the
available evidence.
"""
    _make_case(tmp_path, WEAK_CLAIM, assessment)
    assert validate_status_prose_consistency.main(str(tmp_path / "cases")) == 0


def test_weak_claim_with_strong_register_fails(tmp_path):
    assessment = """# Title

The c001 claim is established and well-documented in all sources.
"""
    _make_case(tmp_path, WEAK_CLAIM, assessment)
    assert validate_status_prose_consistency.main(str(tmp_path / "cases")) == 1


def test_weak_claim_with_upgrade_phrase_fails(tmp_path):
    assessment = """# Title

The c001 claim shows that in reality the mainstream evaluation was independent.
"""
    _make_case(tmp_path, WEAK_CLAIM, assessment)
    assert validate_status_prose_consistency.main(str(tmp_path / "cases")) == 1


def test_established_claim_with_strong_register_passes(tmp_path):
    assessment = """# Title

The c001 claim is established and documented.
"""
    _make_case(tmp_path, ESTABLISHED_CLAIM, assessment)
    assert validate_status_prose_consistency.main(str(tmp_path / "cases")) == 0


def test_no_verdict_smuggle_fails(tmp_path):
    claim = """schema_version: "1.0"
claims:
  - schema_version: "1.0"
    claim_id: "c001"
    claim_type: "factual_event_claim"
    statement: "The mainstream evaluation was independent of cluster effects in the documented channels."
    status: "no_verdict_possible"
    uncertainty:
      score: 0.9
      causes: ["insufficient evidence"]
    interpolation:
      score: 0.5
      assumptions: ["A"]
"""
    assessment = """# Title

Although no verdict is possible, the most likely explanation for c001 is that
mainstream evaluation was independent of cluster effects.
"""
    _make_case(tmp_path, claim, assessment)
    assert validate_status_prose_consistency.main(str(tmp_path / "cases")) == 1


def test_contradicted_claim_without_exclusion_basis_fails(tmp_path):
    claim = """schema_version: "1.0"
claims:
  - schema_version: "1.0"
    claim_id: "c001"
    claim_type: "factual_event_claim"
    statement: "The Lancet authors had documented institutional ties."
    status: "contradicted"
    evidence_refs: ["e001"]
    source_refs: ["s001"]
    uncertainty:
      score: 0.3
      causes: ["A"]
    interpolation:
      score: 0.2
      assumptions: ["A"]
"""
    assessment = """# Title

The c001 claim is contradicted. The Lancet authors had documented ties but the
explanation is weaker than the alternative.
"""
    _make_case(tmp_path, claim, assessment)
    # Contradicted requires direct exclusion language nearby
    assert validate_status_prose_consistency.main(str(tmp_path / "cases")) == 1


def test_counter_exception_allows_strong_register(tmp_path):
    assessment = """# Title

The c001 claim is weak. The counterhypothesis is well-supported and merits
attention.
"""
    _make_case(tmp_path, WEAK_CLAIM, assessment)
    # "well-supported" is in same sentence as "counterhypothesis" → allowed
    assert validate_status_prose_consistency.main(str(tmp_path / "cases")) == 0


def test_table_row_with_status_cell_does_not_fail(tmp_path):
    assessment = """# Title

| c001 | weak | The claim is underdetermined. |
"""
    _make_case(tmp_path, WEAK_CLAIM, assessment)
    assert validate_status_prose_consistency.main(str(tmp_path / "cases")) == 0


def test_preceding_sentence_in_reference_window_is_checked(tmp_path):
    assessment = """# Title

This is established and documented.
The c001 claim is discussed here in detail.
"""
    _make_case(tmp_path, WEAK_CLAIM, assessment)
    assert validate_status_prose_consistency.main(str(tmp_path / "cases")) == 1
