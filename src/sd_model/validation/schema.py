from __future__ import annotations
import json
from pathlib import Path
from jsonschema import validate as _validate
from jsonschema.exceptions import ValidationError


def validate_json(data: dict, schema_path: Path) -> None:
    """Validate JSON-compatible data against a JSON Schema.

    Raises ValueError with a concise message if validation fails.
    """
    schema = json.loads(Path(schema_path).read_text())
    try:
        _validate(instance=data, schema=schema)
    except ValidationError as e:
        # keep message short but actionable
        location = " / ".join(str(x) for x in e.path) if e.path else "root"
        raise ValueError(f"Schema validation failed at {location}: {e.message}") from e

