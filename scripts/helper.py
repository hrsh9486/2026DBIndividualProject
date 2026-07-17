"""Shared normalisation, metadata, and JSON export helpers.

Source-specific fetching and indicator transformations intentionally live in
their own modules.  This module contains only the reusable boundary shared by
the data pipelines.
"""

from __future__ import annotations

import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from exporters import write_json_atomic


def metadata(
    source: str = "yfinance",
    period: str = "10y",
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build common provenance metadata for a generated dataset."""
    result: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "period": period,
    }
    if extra:
        result.update(extra)
    return result


def ensure_output_dir(output_dir: str | os.PathLike[str]) -> Path:
    """Create an output directory if necessary and return its path."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(
    obj: Any,
    filename: str | os.PathLike[str],
    output_dir: str | os.PathLike[str],
) -> Path:
    """Atomically publish strict, UTF-8 JSON and return the output path.

    JSON is fully written to a temporary file in the destination directory
    before ``os.replace`` publishes it.  Serialization failures therefore
    leave any previously valid output untouched.
    """
    output_path = write_json_atomic(obj, ensure_output_dir(output_dir) / filename)

    print(f"  wrote {output_path}")
    return output_path


def clean_float(value: Any, decimals: int | None = 4) -> float | None:
    """Convert a value to a finite JSON-safe float.

    ``None``, non-numeric values, NaN, and infinities become ``None``.  Set
    ``decimals`` to ``None`` to preserve the converted value without rounding.
    """
    if value is None:
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(number):
        return None
    return round(number, decimals) if decimals is not None else number
