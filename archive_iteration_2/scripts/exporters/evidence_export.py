"""Cross-field-validated atomic evidence publication."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from validators import validate_evidence_report

from .json_export import write_json_atomic


def publish_evidence_report(payload: Any, output_path: str | Path) -> Path:
    validate_evidence_report(payload)
    return write_json_atomic(payload, output_path)
