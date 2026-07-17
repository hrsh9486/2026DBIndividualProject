"""Strict atomic JSON publication."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from validators import validate_payload


def write_json_atomic(payload: Any, output_path: str | Path) -> Path:
    """Write strict JSON beside the target, then atomically replace it."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(payload, temporary_file, indent=2, ensure_ascii=False, allow_nan=False, default=str)
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, destination)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
    return destination


def publish_json(payload: Any, output_path: str | Path, schema_name: str) -> Path:
    """Validate a complete payload before atomically publishing it."""
    validate_payload(payload, schema_name)
    return write_json_atomic(payload, output_path)
