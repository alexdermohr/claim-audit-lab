"""Tests for scripts/validate_source_verification_gate.py."""

import pathlib
import sys
import textwrap

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import validate_source_verification_gate


def _write_case(tmp_path, claims_yaml, sources_yaml, *, path=("history", "case-a")):
    case_dir = tmp_path / "cases"
    for part in path:
        case_dir /= part
    case_dir.mkdir(parents=True)
    (case_dir / "claims.yml").write_text(claims_yaml, encoding="utf-8")
    (case_dir / "sources.yml").write_text(sources_yaml, encoding="utf-8")
    return case_dir


def _claims(status: str, claim_type: str = "factual_event_claim", claim_kind: str | None = None, source_ref: str = "s001") -> str:
    claim_kind_line = f'\n    claim_kind: "{claim_kind}"' if claim_kind else ""
    return textwrap.dedent(
        f"""
        schema_version: "1.0"
        claims:
          - schema_version: "1.0"
            claim_id: "c001"
            claim_type: "{claim_type}"{claim_kind_line}
            statement: "Claim statement"
            status: "{status}"
            source_refs: ["{source_ref}"]
            uncertainty:
              score: 0.2
              causes: ["x"]
            interpolation:
              score: 0.1
              assumptions: ["y"]
        """
    ).strip() + "\n"


def _sources(verification_block: str, notes: str = "") -> str:
    indented_verification = "\n".join(
        f"    {line}" if line.strip() else line for line in verification_block.splitlines()
    )
    notes_line = f'    notes: "{notes}"\n' if notes else ""
    verification_section = f"{indented_verification}\n" if indented_verification else ""
    return (
        'schema_version: "1.0"\n'
        "sources:\n"
        '  - schema_version: "1.0"\n'
        '    source_id: "s001"\n'
        '    label: "Source"\n'
        '    url_or_ref: "https://example.org/source"\n'
        '    source_type: "official_body"\n'
        f"{verification_section}"
        f"{notes_line}"
    )


def test_unverified_source_blocks_established_world_claim(tmp_path):
    _write_case(
        tmp_path,
        _claims(status="established", claim_type="factual_event_claim"),
        _sources(
            textwrap.dedent(
                """
                source_verification:
                  status: "unverified"
                """
            ).rstrip()
        ),
    )
    assert validate_source_verification_gate.main(str(tmp_path / "cases")) == 1


def test_notes_unverified_reference_blocks_strongly_supported(tmp_path):
    _write_case(
        tmp_path,
        _claims(status="strongly_supported", claim_type="narrative_claim"),
        _sources("", notes="UNVERIFIED_REFERENCE (draft)"),
    )
    assert validate_source_verification_gate.main(str(tmp_path / "cases")) == 1


def test_verified_source_allows_established_claim(tmp_path):
    _write_case(
        tmp_path,
        _claims(status="established", claim_type="factual_event_claim"),
        _sources(
            textwrap.dedent(
                """
                source_verification:
                  status: "verified"
                """
            ).rstrip()
        ),
    )
    assert validate_source_verification_gate.main(str(tmp_path / "cases")) == 0


def test_meta_claim_with_local_source_is_exempt(tmp_path):
    _write_case(
        tmp_path,
        _claims(status="established", claim_type="meta_claim"),
        textwrap.dedent(
            """
            schema_version: "1.0"
            sources:
              - schema_version: "1.0"
                source_id: "s001"
                label: "Local scope source"
                url_or_ref: "cases/history/case-a/question.md"
                source_type: "other"
                source_verification:
                  status: "unverified"
                notes: "UNVERIFIED_REFERENCE (draft)"
            """
        ).strip() + "\n",
    )
    assert validate_source_verification_gate.main(str(tmp_path / "cases")) == 0


def test_causal_claim_strongly_supported_with_unverified_source_fails(tmp_path):
    _write_case(
        tmp_path,
        _claims(status="strongly_supported", claim_type="causal_claim"),
        _sources(
            textwrap.dedent(
                """
                source_verification:
                  status: "unverified"
                """
            ).rstrip()
        ),
    )
    assert validate_source_verification_gate.main(str(tmp_path / "cases")) == 1
