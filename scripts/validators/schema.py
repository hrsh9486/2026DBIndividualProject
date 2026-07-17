"""JSON Schema validation for production artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from config import SCHEMA_DIR


class SchemaValidationError(ValueError):
    """Raised with all schema errors before publication is attempted."""


def validate_payload(
    payload: Any,
    schema_name: str,
    schema_dir: str | Path = SCHEMA_DIR,
) -> None:
    schema_path = Path(schema_dir) / schema_name
    with schema_path.open(encoding="utf-8") as schema_file:
        schema = json.load(schema_file)

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors[:10]
        )
        raise SchemaValidationError(f"{schema_name} validation failed: {details}")
