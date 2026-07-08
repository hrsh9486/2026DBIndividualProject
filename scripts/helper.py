import json
import os
from datetime import datetime, timezone
import numpy as np


def metadata(source="yfinance", period="10y", extra=None):
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "period": period,
    }
    if extra:
        meta.update(extra)
    return meta


def write_json(obj, filename, output_dir):
    path = os.path.join(output_dir, filename)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=str)
    print(f"  wrote {path}")


def clean_float(x, decimals=4):
    """Round and convert NaN -> None so it serializes as JSON null."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    return round(float(x), decimals)

