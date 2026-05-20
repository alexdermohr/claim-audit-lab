"""Tests for scripts/validate_verification_language_consistency.py"""

import pathlib
import sys
import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_verification_language_consistency


def _write_case(
    tmp_path,
    case_id: str = "test-case",
    *,
    claims_data: dict | None = None,
    receipt_data: dict | None = None,
    sources_data: dict | None = None,
    evidence_data: dict | None = None,
    assessment_text: str | None = None,
) -> pathlib.Path:
    case_dir = tmp_path / "cases" / "sandbox" / case_id
    case_dir.mkdir(parents=True)
    # Minimal marker for case discovery
    (case_dir / "evidence-relations.yml").write_text(
        "schema_version: '1.0'\nrelations: []\n", encoding="utf-8"
    )
    if claims_data:
        (case_dir / "claims.yml").write_text(
            yaml.dump(claims_data, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
    if receipt_data:
        (case_dir / "answer-receipt.yml").write_text(
            yaml.dump(receipt_data, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
    if sources_data:
        (case_dir / "sources.yml").write_text(
            yaml.dump(sources_data, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
    if evidence_data:
        (case_dir / "evidence-pack.yml").write_text(
            yaml.dump(evidence_data, allow_unicode=True, default_flow_style=False),
            encoding="utf-8",
        )
    if assessment_text is not None:
        (case_dir / "assessment.md").write_text(assessment_text, encoding="utf-8")
    return case_dir


def _receipt(background_only: bool = True, what_would_change: str = "") -> dict:
    return {
        "schema_version": "1.0",
        "question": "Test question.",
        "task_classification": "claim_audit",
        "answer_summary": "Test summary.",
        "verdicts_used": [],
        "counterhypotheses_considered": [],
        "forbidden_upgrades_check": {"upgrades_considered": [], "upgrades_blocked": []},
        "banned_phrases_self_scan": {"scanned": True, "hits": []},
        "source_cluster_audit": {"clusters_identified": [], "independence_verified": True},
        "refusal_check": {"refused": False, "balanced_framing_present": False},
        "external_research": {
            "tools_used": [],
            "sources_consulted": [],
            "background_knowledge_only": background_only,
        },
        "oracle_disclaimer_present": True,
        "final_uncertainty_statement": "background-knowledge-only, no external verification.",
        "what_would_change_assessment": what_would_change or "Additional evidence would change this.",
        "case_ref": "cases/sandbox/test-case",
        "review_date": "2026-05-20",
    }


def _claims(statement: str, notes: str = "", source_refs: list | None = None) -> dict:
    claim = {
        "schema_version": "1.0",
        "claim_id": "c001",
        "claim_type": "factual_event_claim",
        "statement": statement,
        "status": "weak",
        "uncertainty": {"score": 0.3, "causes": ["x"]},
        "interpolation": {"score": 0.1, "assumptions": ["y"]},
    }
    if notes:
        claim["notes"] = notes
    if source_refs is not None:
        claim["source_refs"] = source_refs
    return {"schema_version": "1.0", "claims": [claim]}


def _sources(verification_status: str = "unverified") -> dict:
    return {
        "schema_version": "1.0",
        "sources": [
            {
                "schema_version": "1.0",
                "source_id": "s001",
                "label": "Test Source",
                "url_or_ref": "https://example.org",
                "source_type": "secondary_analysis",
                "source_verification": {"status": verification_status},
            }
        ],
    }


# ---------- Fail tests ----------


def test_background_only_with_positive_verification_language_in_claim_fails(tmp_path):
    """background_knowledge_only: true + claim with positive verification language → fail."""
    _write_case(
        tmp_path,
        case_id="fail-bg-claim",
        claims_data=_claims(
            statement="in verifizierten Quellen nicht nachgewiesen.",
            source_refs=["s001"],
        ),
        receipt_data=_receipt(background_only=True),
        sources_data=_sources("unverified"),
    )
    result = validate_verification_language_consistency.main(str(tmp_path / "cases"))
    assert result == 1, "Expected failure: background-only case with positive verification language"


def test_all_unverified_sources_with_positive_claim_notes_fails(tmp_path):
    """All source_refs unverified + claim notes with 'verified sources show no evidence' → fail."""
    _write_case(
        tmp_path,
        case_id="fail-unverified-notes",
        claims_data=_claims(
            statement="X ist dokumentiert.",
            notes="verified sources show no evidence of coordination.",
            source_refs=["s001"],
        ),
        receipt_data=_receipt(background_only=False),
        sources_data=_sources("unverified"),
    )
    result = validate_verification_language_consistency.main(str(tmp_path / "cases"))
    assert result == 1, "Expected failure: all-unverified sources with positive verification language in notes"


def test_background_only_with_positive_language_in_assessment_fails(tmp_path):
    """background_knowledge_only: true + assessment.md with positive language → fail."""
    _write_case(
        tmp_path,
        case_id="fail-bg-assessment",
        receipt_data=_receipt(background_only=True),
        assessment_text="This claim is supported by externally verified evidence from multiple agencies.",
    )
    result = validate_verification_language_consistency.main(str(tmp_path / "cases"))
    assert result == 1, "Expected failure: background-only with positive language in assessment.md"


def test_negation_in_one_sentence_does_not_exempt_positive_claim_elsewhere(tmp_path):
    """Negation in one sentence must not neutralize positive verification language in another."""
    _write_case(
        tmp_path,
        case_id="fail-sentence-scoped-negation",
        receipt_data=_receipt(background_only=True),
        assessment_text="Not externally verified. Verified sources show no evidence.",
    )
    result = validate_verification_language_consistency.main(str(tmp_path / "cases"))
    assert result == 1, "Expected failure: positive claim in separate sentence must still be flagged"


def test_not_externally_verified_sentence_passes(tmp_path):
    """A purely negated verification sentence is allowed in background-only mode."""
    _write_case(
        tmp_path,
        case_id="pass-negated-english-verification",
        receipt_data=_receipt(background_only=True),
        assessment_text="Not externally verified.",
    )
    result = validate_verification_language_consistency.main(str(tmp_path / "cases"))
    assert result == 0, "Expected pass: negated verification statement should not be flagged"


# ---------- Pass tests ----------


def test_background_only_with_disciplined_absence_language_passes(tmp_path):
    """background_knowledge_only: true + disciplined absence language → pass."""
    _write_case(
        tmp_path,
        case_id="pass-bg-disciplined",
        claims_data=_claims(
            statement="im vorliegenden, als unverified markierten Quellenpaket nicht belegt.",
            source_refs=["s001"],
        ),
        receipt_data=_receipt(background_only=True),
        sources_data=_sources("unverified"),
    )
    result = validate_verification_language_consistency.main(str(tmp_path / "cases"))
    assert result == 0, "Expected pass: disciplined absence language in background-only case"


def test_what_would_change_assessment_with_verified_language_exempt(tmp_path):
    """what_would_change_assessment may contain 'externally verified' without failing."""
    receipt = _receipt(
        background_only=True,
        what_would_change="externally verified evidence would change the assessment.",
    )
    _write_case(
        tmp_path,
        case_id="pass-exempt-field",
        receipt_data=receipt,
    )
    result = validate_verification_language_consistency.main(str(tmp_path / "cases"))
    assert result == 0, "Expected pass: what_would_change_assessment is exempt from the gate"


def test_verified_source_allows_positive_language_in_claim(tmp_path):
    """source_verification.status: verified + positive language in claim → pass."""
    _write_case(
        tmp_path,
        case_id="pass-verified-source",
        claims_data=_claims(
            statement="According to verified sources, the event occurred.",
            source_refs=["s001"],
        ),
        receipt_data=_receipt(background_only=False),
        sources_data=_sources("verified"),
    )
    result = validate_verification_language_consistency.main(str(tmp_path / "cases"))
    assert result == 0, "Expected pass: verified source allows positive language"


def test_no_background_only_flag_no_positive_language_passes(tmp_path):
    """Case without background_knowledge_only flag and without positive language → pass."""
    _write_case(
        tmp_path,
        case_id="pass-no-bg-flag",
        claims_data=_claims(
            statement="Das Ereignis ist dokumentiert.",
            source_refs=["s001"],
        ),
        receipt_data=_receipt(background_only=False),
        sources_data=_sources("verified"),
    )
    result = validate_verification_language_consistency.main(str(tmp_path / "cases"))
    assert result == 0, "Expected pass: no background flag, no positive language"
