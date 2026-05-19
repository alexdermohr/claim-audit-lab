"""Tests for scripts/_jsonschema_fallback.py."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

from _jsonschema_fallback import Draft7Validator


def test_max_length_is_enforced():
    schema = {
        "type": "object",
        "properties": {
            "answer_summary": {"type": "string", "maxLength": 5},
        },
    }
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors({"answer_summary": "123456"}))
    assert errors
    assert "maximum length is 5" in errors[0].message

