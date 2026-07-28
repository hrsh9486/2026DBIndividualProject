"""World Bank API ingestion and immutable raw landing."""

from __future__ import annotations

import hashlib
import json
import time
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from config import RAW_DATA_DIR, REQUEST_TIMEOUT, RETRY_ATTEMPTS, RETRY_BACKOFF_SECONDS, WB_BASE
from exporters import write_json_atomic


@dataclass(frozen=True, slots=True)
class WorldBankResponse:
    payload: list[Any]
    source_url: str
    retrieved_at: str
    raw_path: Path
    checksum: str


class WorldBankExtractor:
    """Fetch World Bank payloads without applying indicator transformations."""

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        raw_root: str | Path = RAW_DATA_DIR / "world_bank",
    ) -> None:
        self.session = session or requests.Session()
        self.raw_root = Path(raw_root)

    def fetch(self, country: str, indicator: str, start_year: int, end_year: int) -> WorldBankResponse:
        url = f"{WB_BASE}/country/{country}/indicator/{indicator}"
        params = {
            "format": "json",
            "per_page": 1000,
            "date": f"{start_year}:{end_year}",
        }
        last_error: Exception | None = None
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, list):
                    raise ValueError("World Bank response must be a JSON array")
                return self._land_raw(payload, response.url, country, indicator)
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt < RETRY_ATTEMPTS:
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)
        cached = self._load_latest(country, indicator)
        if cached is not None:
            warnings.warn(
                f"World Bank fetch failed for {country}/{indicator}; using immutable raw snapshot "
                f"from {cached.retrieved_at}: {last_error}",
                RuntimeWarning,
                stacklevel=2,
            )
            return cached
        raise RuntimeError(f"World Bank fetch failed for {country}/{indicator}: {last_error}")

    def _load_latest(self, country: str, indicator: str) -> WorldBankResponse | None:
        """Recover from transient API failures using the newest landed snapshot."""
        candidates = sorted(
            self.raw_root.glob(f"*/{indicator}/{country}-*.json"),
            key=lambda path: (path.parent.parent.name, path.name),
            reverse=True,
        )
        for raw_path in candidates:
            try:
                envelope = json.loads(raw_path.read_text(encoding="utf-8"))
                payload = envelope["payload"]
                if not isinstance(payload, list):
                    continue
                return WorldBankResponse(
                    payload=payload,
                    source_url=str(envelope["source_url"]),
                    retrieved_at=str(envelope["retrieved_at"]),
                    raw_path=raw_path,
                    checksum=str(envelope["sha256"]),
                )
            except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError):
                continue
        return None

    def _land_raw(
        self,
        payload: list[Any],
        source_url: str,
        country: str,
        indicator: str,
    ) -> WorldBankResponse:
        retrieved = datetime.now(timezone.utc)
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        checksum = hashlib.sha256(serialized).hexdigest()
        directory = self.raw_root / retrieved.date().isoformat() / indicator
        raw_path = directory / f"{country}-{checksum[:12]}.json"
        if not raw_path.exists():
            write_json_atomic(
                {
                    "retrieved_at": retrieved.isoformat(),
                    "source_url": source_url,
                    "sha256": checksum,
                    "payload": payload,
                },
                raw_path,
            )
        return WorldBankResponse(
            payload=payload,
            source_url=source_url,
            retrieved_at=retrieved.isoformat(),
            raw_path=raw_path,
            checksum=checksum,
        )
