"""Accumulate NSE's provisional daily FII/FPI and DII cash-market activity."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import requests

from config import RAW_DATA_DIR, REQUEST_TIMEOUT


NSE_REPORT_URL = "https://www.nseindia.com/reports/fii-dii"
NSE_API_URL = "https://www.nseindia.com/api/fiidiiTradeReact"
_USER_AGENT = "Mozilla/5.0 (compatible; India-research-pipeline/1.0; academic research)"


@dataclass(frozen=True, slots=True)
class InstitutionalFlowDaily:
    date: date
    category: str
    buy_crore: float
    sell_crore: float
    net_crore: float


@dataclass(frozen=True, slots=True)
class NseInstitutionalFlowResponse:
    observations: tuple[InstitutionalFlowDaily, ...]
    source_url: str
    retrieved_at: str
    raw_path: Path
    checksum: str


def parse_nse_flow_rows(rows: list[dict]) -> tuple[InstitutionalFlowDaily, ...]:
    observations = []
    for row in rows:
        category = str(row.get("category", "")).strip().upper()
        if category == "DII":
            normalised_category = "DII"
        elif category in {"FII", "FPI", "FII/FPI"}:
            normalised_category = "FPI"
        else:
            continue
        observation = InstitutionalFlowDaily(
            date=datetime.strptime(str(row["date"]), "%d-%b-%Y").date(),
            category=normalised_category,
            buy_crore=float(str(row["buyValue"]).replace(",", "")),
            sell_crore=float(str(row["sellValue"]).replace(",", "")),
            net_crore=float(str(row["netValue"]).replace(",", "")),
        )
        if abs((observation.buy_crore - observation.sell_crore) - observation.net_crore) > 0.02:
            raise ValueError(f"NSE net flow does not reconcile for {observation.category} on {observation.date}")
        observations.append(observation)
    categories = {item.category for item in observations}
    if categories != {"DII", "FPI"}:
        raise ValueError("NSE response must contain both DII and FII/FPI rows")
    return tuple(sorted(observations, key=lambda item: (item.date, item.category)))


class NseInstitutionalFlowExtractor:
    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        raw_root: str | Path = RAW_DATA_DIR / "nse-institutional-flows",
    ) -> None:
        self.session = session or requests.Session()
        self.raw_root = Path(raw_root)

    def fetch(self) -> NseInstitutionalFlowResponse:
        headers = {"User-Agent": _USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
        landing = self.session.get(NSE_REPORT_URL, headers=headers, timeout=REQUEST_TIMEOUT)
        landing.raise_for_status()
        response = self.session.get(
            NSE_API_URL,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept": "application/json,text/plain,*/*",
                "Referer": NSE_REPORT_URL,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        rows = response.json()
        observations = parse_nse_flow_rows(rows)
        retrieved_at = datetime.now(timezone.utc).isoformat()
        canonical_bytes = json.dumps(rows, ensure_ascii=False, sort_keys=True).encode("utf-8")
        checksum = hashlib.sha256(canonical_bytes).hexdigest()
        raw_path = self.raw_root / retrieved_at[:10] / f"fii-dii-{checksum[:12]}.json"
        if not raw_path.exists():
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(
                json.dumps(
                    {"retrieved_at": retrieved_at, "rows": rows},
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

        archive: dict[tuple[date, str], tuple[datetime, InstitutionalFlowDaily]] = {}
        for path in sorted(self.raw_root.glob("*/*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                archived_rows = payload["rows"]
                archived_at = datetime.fromisoformat(payload["retrieved_at"])
            else:
                # Backward compatibility for the first raw snapshots, which
                # stored the provider array directly.
                archived_rows = payload
                archived_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            for item in parse_nse_flow_rows(archived_rows):
                key = (item.date, item.category)
                prior = archive.get(key)
                if prior is None or archived_at >= prior[0]:
                    archive[key] = (archived_at, item)
        return NseInstitutionalFlowResponse(
            observations=tuple(sorted(
                (item for _, item in archive.values()),
                key=lambda item: (item.date, item.category),
            )),
            source_url=response.url,
            retrieved_at=retrieved_at,
            raw_path=raw_path,
            checksum=checksum,
        )
