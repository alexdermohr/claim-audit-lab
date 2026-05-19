"""Tests for scripts/validate_aggregation_discipline.py."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_aggregation_discipline


def _make_case(tmp_path, claims, relations, robustness=None, name="case-a"):
    case_dir = tmp_path / "cases" / "history" / name
    case_dir.mkdir(parents=True)
    (case_dir / "claims.yml").write_text(claims, encoding="utf-8")
    (case_dir / "evidence-relations.yml").write_text(relations, encoding="utf-8")
    if robustness is not None:
        (case_dir / "source-cluster-robustness.yml").write_text(robustness, encoding="utf-8")
    return case_dir


REPORTED_CLAIM_AGGREGATION = """schema_version: "1.0"
claims:
  - schema_version: "1.0"
    claim_id: "c001"
    claim_type: "factual_event_claim"
    statement: "X happened"
    status: "established"
    evidence_refs: ["e001", "e002", "e003", "e004", "e005"]
    source_refs: ["s001"]
    uncertainty:
      score: 0.1
      causes: ["A"]
    interpolation:
      score: 0.05
      assumptions: ["A"]
"""

REPORTS_ONLY_RELATIONS = """schema_version: "1.0"
case_ref: "cases/history/case-a"
relations:
  - relation_id: r1
    evidence_ref: e001
    claim_ref: c001
    relation_type: reports
  - relation_id: r2
    evidence_ref: e002
    claim_ref: c001
    relation_type: reports
  - relation_id: r3
    evidence_ref: e003
    claim_ref: c001
    relation_type: reports
  - relation_id: r4
    evidence_ref: e004
    claim_ref: c001
    relation_type: reports
  - relation_id: r5
    evidence_ref: e005
    claim_ref: c001
    relation_type: reports
"""

MIXED_RELATIONS = """schema_version: "1.0"
case_ref: "cases/history/case-a"
relations:
  - relation_id: r1
    evidence_ref: e001
    claim_ref: c001
    relation_type: reports
  - relation_id: r2
    evidence_ref: e002
    claim_ref: c001
    relation_type: reports
  - relation_id: r3
    evidence_ref: e006
    claim_ref: c001
    relation_type: supports_directly
"""

ROBUSTNESS_ALLOWS_INDEPENDENCE = """schema_version: "1.0"
case_ref: "cases/history/case-a"
clusters:
  - cluster_ref: c001
    independence_verified: true
robustness_tests:
  - claim_ref: c001
    independence_verified: true
"""


def test_pure_reports_aggregation_fails(tmp_path):
    _make_case(tmp_path, REPORTED_CLAIM_AGGREGATION, REPORTS_ONLY_RELATIONS)
    assert validate_aggregation_discipline.main(str(tmp_path / "cases")) == 1


def test_mixed_relations_pass(tmp_path):
    _make_case(tmp_path, REPORTED_CLAIM_AGGREGATION, MIXED_RELATIONS)
    assert validate_aggregation_discipline.main(str(tmp_path / "cases")) == 0


def test_reports_only_with_robustness_passes(tmp_path):
    _make_case(
        tmp_path,
        REPORTED_CLAIM_AGGREGATION,
        REPORTS_ONLY_RELATIONS,
        robustness=ROBUSTNESS_ALLOWS_INDEPENDENCE,
    )
    assert validate_aggregation_discipline.main(str(tmp_path / "cases")) == 0


def test_weak_claim_with_reports_only_passes(tmp_path):
    # Weak claims don't trigger aggregation discipline (only strongly_supported/established)
    weak = REPORTED_CLAIM_AGGREGATION.replace('status: "established"', 'status: "weak"')
    _make_case(tmp_path, weak, REPORTS_ONLY_RELATIONS)
    assert validate_aggregation_discipline.main(str(tmp_path / "cases")) == 0


def test_reported_claim_burden_profile_skips_check(tmp_path):
    claim = REPORTED_CLAIM_AGGREGATION.replace(
        'claim_type: "factual_event_claim"',
        'claim_type: "factual_event_claim"\n    claim_kind: "reported_claim"\n    burden_profile: "source_report"',
    )
    _make_case(tmp_path, claim, REPORTS_ONLY_RELATIONS)
    # Reported claim with source_report burden_profile is intentionally
    # source-bounded, not a world claim, so aggregation discipline doesn't apply.
    assert validate_aggregation_discipline.main(str(tmp_path / "cases")) == 0
