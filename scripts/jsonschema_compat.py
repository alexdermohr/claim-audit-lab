"""Import the real jsonschema package, falling back to a local subset if absent."""

try:
    import jsonschema  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - exercised only in constrained envs
    import _jsonschema_fallback as jsonschema  # type: ignore[no-redef]
