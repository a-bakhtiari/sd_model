from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def validate_json_schema(instance: Dict[str, Any], schema_path: Path) -> None:
    """Validate an instance dict against a JSON Schema file.

    If `jsonschema` is unavailable, the function becomes a no-op to avoid
    blocking development in minimal environments.
    """
    try:
        from jsonschema import Draft7Validator  # type: ignore
    except Exception:
        return  # No-op when validator is not installed

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: e.path)
    if errors:
        first = errors[0]
        raise ValueError(f"Schema validation error at {list(first.path)}: {first.message}")

