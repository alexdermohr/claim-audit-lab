"""Tests for scripts/validate_verdict_discipline.py"""

from datetime import date, timedelta
import json
import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_verdict_discipline

SCHEMA_PATH = pathlib.Path(__file__).parent.parent / "schemas" / "evidence-relation.v1.schema.json"
VERDICT_FIXTURE_ROOT = pathlib.Path(__file__).parent / "fixtures" / "verdict_discipline"


def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def write_yaml(path: pathlib.Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False)


def base_claim(status="weak", claim_type="causal_claim", claim_kind="causal_claim", **overrides):
    claim = {
        "schema_version": "1.0",
        "claim_id": "c001",
        "claim_type": claim_type,
        "claim_kind": claim_kind,
        "statement": "Synthetic proposition under evaluation.",
        "status": status,
        "evidence_refs": ["e001"],
        "source_refs": ["s001"],
        "requires": ["required_link"],
        "counterclaims": ["Counterclaim placeholder one.", "Counterclaim placeholder two."],
        "forbidden_upgrades": ["correlation_to_causation"],
        "uncertainty": {"score": 0.4, "causes": ["fixture uncertainty"]},
        "interpolation": {"score": 0.2, "assumptions": ["fixture assumption"]},
        "notes": "Fixture claim.",
    }
    claim.update(overrides)
    return claim


def base_sources(source_type="official_body"):
    return {
        "schema_version": "1.0",
        "sources": [
            {
                "schema_version": "1.0",
                "source_id": "s001",
                "label": "Fixture source",
                "url_or_ref": "https://example.org/source",
                "source_type": source_type,
            }
        ],
    }


def base_evidence_pack(contradicts=None, supports=None, claim_refs=None):
    return {
        "schema_version": "1.0",
        "evidence": [
            {
                "evidence_id": "e001",
                "source_ref": "s001",
                "claim_refs": ["c001"] if claim_refs is None else claim_refs,
                "type": "official_statement",
                "summary": "Fixture evidence summary.",
                "verbatim_or_ref": "Fixture source reference.",
                "supports": [] if supports is None else supports,
                "contradicts": [] if contradicts is None else contradicts,
            }
        ],
    }


def base_relations(relation_type="weakens", **overrides):
    relation = {
        "relation_id": "r001",
        "evidence_ref": "e001",
        "claim_ref": "c001",
        "relation_type": relation_type,
        "strength": 0.7,
        "explanation": "Fixture relation explanation.",
    }
    relation.update(overrides)
    return {"schema_version": "1.0", "case_ref": "cases/test", "relations": [relation]}


def write_case(
    tmp_path,
    claim=None,
    relations=None,
    sources=None,
    evidence_contradicts=None,
    evidence_supports=None,
    evidence_claim_refs=None,
):
    write_yaml(tmp_path / "claims.yml", {"schema_version": "1.0", "claims": [claim or base_claim()]})
    write_yaml(tmp_path / "sources.yml", sources or base_sources())
    write_yaml(
        tmp_path / "evidence-pack.yml",
        base_evidence_pack(evidence_contradicts, evidence_supports, evidence_claim_refs),
    )
    if relations is not None:
        write_yaml(tmp_path / "evidence-relations.yml", relations)


def test_claims_and_evidence_pack_require_evidence_relations_file(tmp_path):
    write_case(tmp_path, relations=None)
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any(
        "evidence-relations.yml required because claims.yml and evidence-pack.yml exist." in e
        for e in errors
    ), errors


def test_cli_discovers_claims_and_evidence_pack_case_without_relations(tmp_path, capsys):
    case_dir = tmp_path / "synthetic-case"
    write_case(case_dir, relations=None)
    exit_code = validate_verdict_discipline.main(str(tmp_path))
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL" in captured.out
    assert "evidence-relations.yml required because claims.yml and evidence-pack.yml exist." in captured.out


def test_legacy_supports_without_positive_relation_fails(tmp_path):
    claim = base_claim(status="weak")
    write_case(tmp_path, claim=claim, relations=base_relations("contextualizes"), evidence_supports=["c001"])
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("Legacy evidence-pack supports requires" in e for e in errors), errors


def test_legacy_supports_allows_positive_relation(tmp_path):
    claim = base_claim(status="weak")
    write_case(tmp_path, claim=claim, relations=base_relations("supports_indirectly"), evidence_supports=["c001"])
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert errors == []


def test_legacy_supports_reports_requires_reported_claim(tmp_path):
    claim = base_claim(status="weak", claim_type="factual_event_claim", claim_kind="factual_event_claim")
    write_case(tmp_path, claim=claim, relations=base_relations("reports"), evidence_supports=["c001"])
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("or reports for a reported/source-report claim" in e for e in errors), errors


def test_legacy_supports_reports_allows_source_report_claim(tmp_path):
    claim = base_claim(
        status="plausible",
        claim_type="meta_claim",
        claim_kind="reported_claim",
        burden_profile="source_report",
    )
    write_case(tmp_path, claim=claim, relations=base_relations("reports"), evidence_supports=["c001"])
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert errors == []


def test_relation_must_be_mirrored_by_claim_evidence_refs(tmp_path):
    claim = base_claim(status="weak", evidence_refs=[])
    write_case(tmp_path, claim=claim, relations=base_relations("weakens"))
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("Evidence relation must be mirrored" in e for e in errors), errors


def test_relation_must_be_mirrored_by_evidence_claim_refs(tmp_path):
    claim = base_claim(status="weak")
    write_case(tmp_path, claim=claim, relations=base_relations("weakens"), evidence_claim_refs=[])
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("Evidence relation must be mirrored" in e for e in errors), errors


def test_relation_requires_evidence_pack(tmp_path):
    claim = base_claim(status="weak")
    write_yaml(tmp_path / "claims.yml", {"schema_version": "1.0", "claims": [claim]})
    write_yaml(tmp_path / "sources.yml", base_sources())
    write_yaml(tmp_path / "evidence-relations.yml", base_relations("supports_indirectly"))
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("evidence-pack.yml is missing" in e for e in errors), errors


def test_legacy_contradicts_without_direct_relation_fails(tmp_path):
    claim = base_claim(status="weak")
    write_case(tmp_path, claim=claim, relations=base_relations("weakens"), evidence_contradicts=["c001"])
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("Legacy evidence-pack contradicts requires contradicts_directly" in e for e in errors), errors


def test_evidence_pack_weakens_only_must_not_use_contradicts(tmp_path):
    claim = base_claim(status="weak")
    write_case(tmp_path, claim=claim, relations=base_relations("weakens"), evidence_contradicts=["c001"])
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("Legacy evidence-pack contradicts" in e for e in errors), errors


def test_legacy_contradicts_with_direct_relation_passes(tmp_path):
    write_case(
        tmp_path,
        claim=base_claim(
            status="contradicted",
            burden_profile="causal_chain",
            required_chain=[{"id": "required_link", "requirement": "Required link.", "status": "satisfied"}],
        ),
        relations=base_relations(
            "contradicts_directly",
            incompatible_proposition="Fixture incompatible proposition.",
        ),
        evidence_contradicts=["c001"],
    )
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert errors == []


def test_contradicted_without_direct_contradiction_fails(tmp_path):
    write_case(tmp_path, claim=base_claim(status="contradicted"), relations=base_relations("weakens"))
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("requires at least one" in e and "contradicts_directly" in e for e in errors), errors


def test_alternative_explanation_does_not_allow_contradicted(tmp_path):
    write_case(
        tmp_path,
        claim=base_claim(status="contradicted"),
        relations=base_relations("alternative_explanation"),
    )
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("cannot be 'contradicted'" in e for e in errors), errors


def test_missing_link_does_not_allow_contradicted(tmp_path):
    write_case(tmp_path, claim=base_claim(status="contradicted"), relations=base_relations("missing_link"))
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("cannot be 'contradicted'" in e for e in errors), errors


def test_contradicted_causal_claim_requires_burden_profile_or_chain(tmp_path):
    write_case(
        tmp_path,
        claim=base_claim(status="contradicted"),
        relations=base_relations(
            "contradicts_directly",
            incompatible_proposition="Fixture incompatible proposition.",
        ),
    )
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("requires burden_profile" in e for e in errors), errors


def test_direct_contradiction_requires_incompatible_proposition(tmp_path):
    write_case(
        tmp_path,
        claim=base_claim(
            status="contradicted",
            burden_profile="causal_chain",
            required_chain=[{"id": "required_link", "requirement": "Required link.", "status": "satisfied"}],
        ),
        relations=base_relations("contradicts_directly"),
    )
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("incompatible_proposition" in e for e in errors), errors


def test_direct_contradiction_allows_contradicted(tmp_path):
    write_case(
        tmp_path,
        claim=base_claim(
            status="contradicted",
            burden_profile="causal_chain",
            required_chain=[{"id": "required_link", "requirement": "Required link.", "status": "satisfied"}],
        ),
        relations=base_relations(
            "contradicts_directly",
            incompatible_proposition="Fixture incompatible proposition.",
        ),
    )
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert errors == []


def test_reported_claim_does_not_establish_world_causal_claim(tmp_path):
    write_case(
        tmp_path,
        claim=base_claim(status="established", claim_type="causal_claim", claim_kind="reported_claim"),
        relations=base_relations("reports"),
    )
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("split source report from world-causal claim" in e for e in errors), errors


def test_reported_claim_established_allows_reports_relation(tmp_path):
    claim = base_claim(status="established", claim_type="meta_claim", claim_kind="reported_claim")
    write_case(tmp_path, claim=claim, relations=base_relations("reports"))
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert errors == []


def test_strong_claim_without_positive_relation_fails(tmp_path):
    claim = base_claim(status="established", claim_type="factual_event_claim", claim_kind="factual_event_claim")
    write_case(tmp_path, claim=claim, relations=base_relations("contextualizes"), sources=base_sources("peer_reviewed"))
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("positive typed evidence relation" in e for e in errors), errors


def test_official_cluster_uses_positive_evidence_sources_not_claim_metadata(tmp_path):
    sources = base_sources("government_report")
    sources["sources"].append(
        {
            "schema_version": "1.0",
            "source_id": "s002",
            "label": "Fixture non-authority source",
            "url_or_ref": "https://example.org/background",
            "source_type": "peer_reviewed",
        }
    )
    claim = base_claim(
        status="strongly_supported",
        burden_profile="causal_chain",
        required_chain=[{"id": "required_link", "requirement": "Required link.", "status": "satisfied"}],
        source_refs=["s001", "s002"],
    )
    write_case(tmp_path, claim=claim, relations=base_relations("supports_directly"), sources=sources)
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("official/government source cluster" in e for e in errors), errors


def test_positive_evidence_unknown_source_ref_fails(tmp_path):
    claim = base_claim(
        status="strongly_supported",
        burden_profile="causal_chain",
        required_chain=[{"id": "required_link", "requirement": "Required link.", "status": "satisfied"}],
    )
    evidence_pack = base_evidence_pack()
    evidence_pack["evidence"][0]["source_ref"] = "s999"
    write_case(
        tmp_path,
        claim=claim,
        relations=base_relations("supports_directly"),
        sources=base_sources("peer_reviewed"),
    )
    write_yaml(tmp_path / "evidence-pack.yml", evidence_pack)
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("Positive evidence source_ref 's999'" in e for e in errors), errors


def test_relation_processing_continues_after_unrelated_prior_errors(tmp_path):
    write_case(
        tmp_path,
        claim=base_claim(
            status="contradicted",
            burden_profile="causal_chain",
            required_chain=[{"id": "required_link", "requirement": "Required link.", "status": "satisfied"}],
        ),
        relations=base_relations(
            "contradicts_directly",
            incompatible_proposition="Fixture incompatible proposition.",
        ),
        evidence_contradicts=["c001"],
    )
    write_yaml(tmp_path / "sources.yml", ["not", "an", "object"])
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("sources.yml must contain a YAML object" in e for e in errors), errors
    assert not any("requires at least one" in e and "contradicts_directly" in e for e in errors), errors
    assert not any("Legacy evidence-pack contradicts requires" in e for e in errors), errors


def test_official_single_cluster_caps_world_causal_claim(tmp_path):
    write_case(
        tmp_path,
        claim=base_claim(
            status="strongly_supported",
            burden_profile="causal_chain",
            required_chain=[
                {"id": "required_link", "requirement": "Required link.", "status": "satisfied"}
            ],
        ),
        relations=base_relations("supports_directly"),
        sources=base_sources("government_report"),
    )
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("official/government source cluster" in e for e in errors), errors


def test_strong_causal_claim_requires_burden_profile_or_chain(tmp_path):
    write_case(
        tmp_path,
        claim=base_claim(status="strongly_supported"),
        relations=base_relations("supports_directly"),
        sources=base_sources("peer_reviewed"),
    )
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("requires burden_profile" in e for e in errors), errors


def test_missing_chain_caps_strong_causal_claim(tmp_path):
    write_case(
        tmp_path,
        claim=base_claim(
            status="established",
            burden_profile="causal_chain",
            required_chain=[
                {"id": "required_link", "requirement": "Required link.", "status": "missing"}
            ],
        ),
        relations=base_relations("supports_directly"),
        sources=base_sources("peer_reviewed"),
    )
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("missing or contested required_chain" in e for e in errors), errors


def test_downgraded_hypothesis_requires_support_ledger(tmp_path):
    write_case(tmp_path, relations=base_relations("supports_indirectly"))
    write_yaml(
        tmp_path / "hypotheses.yml",
        {
            "schema_version": "1.0",
            "hypotheses": [
                {
                    "id": "h1",
                    "label": "fixture_hypothesis",
                    "description": "Fixture hypothesis.",
                    "status": "weak",
                    "supporting_evidence": [],
                    "weaknesses": [],
                }
            ],
        },
    )
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("hypothesis-support-ledger" in e for e in errors), errors



def test_synthetic_minimal_verdict_discipline_case_passes(tmp_path):
    write_case(tmp_path, claim=base_claim(status="weak"), relations=base_relations("supports_indirectly"))
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert errors == [], "synthetic minimal verdict case has errors:\n" + "\n".join(errors)


def test_fixture_contradicted_without_direct_relation_fails():
    errors = validate_verdict_discipline.validate_case(
        VERDICT_FIXTURE_ROOT / "invalid" / "contradicted_without_direct_relation",
        load_schema(),
    )
    assert any("requires at least one" in e and "contradicts_directly" in e for e in errors), errors


def test_fixture_claims_with_missing_relations_file_fails():
    errors = validate_verdict_discipline.validate_case(
        VERDICT_FIXTURE_ROOT / "invalid" / "claims_with_missing_relations_file",
        load_schema(),
    )
    assert any("evidence-relations.yml required" in e for e in errors), errors


def test_fixture_reports_used_as_world_causal_proof_fails():
    errors = validate_verdict_discipline.validate_case(
        VERDICT_FIXTURE_ROOT / "invalid" / "reports_used_as_world_causal_proof",
        load_schema(),
    )
    assert any("requires a positive typed evidence relation" in e for e in errors), errors
    assert any("cannot be established only from source-report relations" in e for e in errors), errors


def test_verdict_discipline_still_requires_relations_for_claims_and_evidence_even_with_legacy_marker(tmp_path):
    today = date.today()
    write_case(tmp_path, relations=None)
    write_yaml(
        tmp_path / "legacy-case.yml",
        {
            "legacy_case": True,
            "created_at": today.isoformat(),
            "expires_on": (today + timedelta(days=60)).isoformat(),
            "migration_target": "Fixture migration target.",
            "reason": "Fixture legacy reason.",
        },
    )
    errors = validate_verdict_discipline.validate_case(tmp_path, load_schema())
    assert any("evidence-relations.yml required" in e for e in errors), errors


def test_cli_verdict_discipline_still_requires_relations_even_with_legacy_marker(tmp_path, capsys):
    today = date.today()
    case_dir = tmp_path / "legacy-case"
    write_case(case_dir, relations=None)
    write_yaml(
        case_dir / "legacy-case.yml",
        {
            "legacy_case": True,
            "created_at": today.isoformat(),
            "expires_on": (today + timedelta(days=60)).isoformat(),
            "migration_target": "Fixture migration target.",
            "reason": "Fixture legacy reason.",
        },
    )
    exit_code = validate_verdict_discipline.main(str(tmp_path))
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "LEGACY" in captured.out
    assert "verdict discipline still enforced" in captured.out
    assert "evidence-relations.yml required because claims.yml and evidence-pack.yml exist." in captured.out
