"""Official Nifty Indices total-return history extraction."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests

from config import RAW_DATA_DIR, REQUEST_TIMEOUT
from exporters import write_json_atomic


PAGE_URL = "https://www.niftyindices.com/reports/historical-data"
TRI_URL = "https://www.niftyindices.com/BackPage/getTotalReturnIndexString"


class NiftyIndicesExtractor:
    def __init__(self, *, raw_root: str | Path = RAW_DATA_DIR / "nifty-indices") -> None:
        self.raw_root = Path(raw_root)

    def fetch_total_return_indices(
        self,
        names: dict[str, str],
        *,
        start_year: int,
        end_date: date | None = None,
    ) -> pd.DataFrame:
        """Fetch official TRI values in provider-required windows of at most one year."""
        end_date = end_date or datetime.now(timezone.utc).date()
        session = requests.Session()
        headers = {"User-Agent": "India-CapEx-research/1.0", "Referer": PAGE_URL}
        session.get(PAGE_URL, headers=headers, timeout=REQUEST_TIMEOUT).raise_for_status()
        columns = {}
        retrieved_at = datetime.now(timezone.utc)
        for key, name in names.items():
            rows: dict[pd.Timestamp, float] = {}
            for year in range(start_year, end_date.year + 1):
                window_start = date(year, 4, 1)
                window_end = min(date(year + 1, 3, 31), end_date)
                if window_start > end_date:
                    continue
                request_info = {
                    "name": name.upper(),
                    "startDate": window_start.strftime("%d-%b-%Y"),
                    "endDate": window_end.strftime("%d-%b-%Y"),
                    "indexName": name.upper(),
                }
                response = session.post(
                    TRI_URL,
                    headers={**headers, "Content-Type": "application/json; charset=utf-8"},
                    json={"cinfo": str(request_info)},
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, list):
                    raise ValueError(f"Unexpected Nifty response for {name}: {type(payload).__name__}")
                for item in payload:
                    value = item.get("TotalReturnsIndex")
                    if value not in (None, ""):
                        rows[pd.Timestamp(item["Date"])] = float(str(value).replace(",", ""))
            if not rows:
                raise ValueError(f"Nifty Indices returned no TRI history for {name}")
            columns[key] = pd.Series(rows).sort_index()
            self._land(key, name, columns[key], retrieved_at)
        return pd.DataFrame(columns).sort_index()

    def _land(self, key: str, name: str, series: pd.Series, retrieved_at: datetime) -> Path:
        observations = [
            {"date": date_value.strftime("%Y-%m-%d"), "tri": float(value)}
            for date_value, value in series.items()
        ]
        checksum = hashlib.sha256(
            json.dumps(observations, sort_keys=True).encode("utf-8")
        ).hexdigest()
        payload = {
            "retrieved_at": retrieved_at.isoformat(),
            "source_url": PAGE_URL,
            "index_name": name,
            "series_type": "total_return_index",
            "sha256": checksum,
            "observations": observations,
        }
        path = self.raw_root / retrieved_at.date().isoformat() / f"{key}-{checksum[:12]}.json"
        if not path.exists():
            write_json_atomic(payload, path)
        return path
