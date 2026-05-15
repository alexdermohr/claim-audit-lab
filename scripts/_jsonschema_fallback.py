"""Small local subset of jsonschema used by this repository's validators.

This fallback keeps the MVP validation scripts runnable in constrained
sandboxes where the third-party ``jsonschema`` package is unavailable.  It is
not a complete JSON Schema implementation; it implements only the Draft 7
keywords used by schemas in this repository.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any, Iterable


@dataclass
class ValidationError(Exception):
    message: str
    absolute_path: list[Any]


class FormatChecker:
    """Placeholder matching the third-party jsonschema API used in scripts."""


def _type_matches(instance: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "null":
        return instance is None
    return True


class Draft7Validator:
    def __init__(self, schema: dict[str, Any], format_checker: FormatChecker | None = None):
        self.schema = schema
        self.format_checker = format_checker

    def iter_errors(self, instance: Any) -> Iterable[ValidationError]:
        yield from self._validate(instance, self.schema, [])

    def _validate(self, instance: Any, schema: dict[str, Any], path: list[Any]):
        expected_type = schema.get("type")
        if isinstance(expected_type, list):
            if not any(_type_matches(instance, t) for t in expected_type):
                yield ValidationError(
                    f"{instance!r} is not of type {expected_type!r}", path.copy()
                )
                return
        elif expected_type and not _type_matches(instance, expected_type):
            yield ValidationError(f"{instance!r} is not of type '{expected_type}'", path.copy())
            return

        if "const" in schema and instance != schema["const"]:
            yield ValidationError(f"{schema['const']!r} was expected", path.copy())

        if "enum" in schema and instance not in schema["enum"]:
            yield ValidationError(f"{instance!r} is not one of {schema['enum']!r}", path.copy())

        if isinstance(instance, dict):
            required = schema.get("required", [])
            for key in required:
                if key not in instance:
                    yield ValidationError(f"'{key}' is a required property", path.copy())

            properties = schema.get("properties", {})
            if schema.get("additionalProperties") is False:
                for key in instance:
                    if key not in properties:
                        yield ValidationError(
                            f"Additional properties are not allowed ({key!r} was unexpected)",
                            path.copy(),
                        )

            for key, value in instance.items():
                if key in properties:
                    yield from self._validate(value, properties[key], path + [key])

        if isinstance(instance, list):
            min_items = schema.get("minItems")
            if min_items is not None and len(instance) < min_items:
                yield ValidationError(
                    f"{instance!r} is too short; minimum is {min_items}", path.copy()
                )
            if schema.get("uniqueItems") is True:
                seen: set[str] = set()
                for item in instance:
                    marker = repr(item)
                    if marker in seen:
                        yield ValidationError(f"{instance!r} has non-unique elements", path.copy())
                        break
                    seen.add(marker)
            item_schema = schema.get("items")
            if isinstance(item_schema, dict):
                for index, item in enumerate(instance):
                    yield from self._validate(item, item_schema, path + [index])

        if isinstance(instance, str):
            min_length = schema.get("minLength")
            if min_length is not None and len(instance) < min_length:
                yield ValidationError(
                    f"{instance!r} is too short; minimum length is {min_length}", path.copy()
                )
            pattern = schema.get("pattern")
            if pattern and re.search(pattern, instance) is None:
                yield ValidationError(
                    f"{instance!r} does not match {pattern!r}", path.copy()
                )
            if schema.get("format") == "date":
                try:
                    date.fromisoformat(instance)
                except ValueError:
                    yield ValidationError(f"{instance!r} is not a 'date'", path.copy())

        if isinstance(instance, (int, float)) and not isinstance(instance, bool):
            minimum = schema.get("minimum")
            if minimum is not None and instance < minimum:
                yield ValidationError(f"{instance!r} is less than the minimum of {minimum}", path.copy())
            maximum = schema.get("maximum")
            if maximum is not None and instance > maximum:
                yield ValidationError(
                    f"{instance!r} is greater than the maximum of {maximum}", path.copy()
                )
