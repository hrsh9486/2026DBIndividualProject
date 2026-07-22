"""NPCI UPI product-statistics extraction and immutable raw landing."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import requests

from config import RAW_DATA_DIR, REQUEST_TIMEOUT
from exporters import write_json_atomic


NPCI_UPI_STATISTICS_URL = "https://www.npci.org.in/product/upi/product-statistics"
NPCI_STATISTICS_TABS_URL = "https://www.npci.org.in/api/product-statistic/tabs"
NPCI_STATISTICS_DETAIL_URL = "https://www.npci.org.in/api/product-statistic/tab/detail"
_USER_AGENT = "India-research-pipeline/1.0 (+academic research)"
_MONTHS = {
    name.lower(): number
    for number, name in enumerate(
        ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"),
        start=1,
    )
}


@dataclass(frozen=True, slots=True)
class UpiMonthlyRecord:
    year: int
    month: int
    volume_millions: float
    value_crore: float
    banks_live: int | None = None


@dataclass(frozen=True, slots=True)
class NpciUpiResponse:
    records: tuple[UpiMonthlyRecord, ...]
    source_url: str
    retrieved_at: str
    raw_path: Path
    checksum: str


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_cell = False
        self.cell_parts: list[str] = []
        self.row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"td", "th"}:
            self.in_cell = True
            self.cell_parts = []

    def handle_data(self, data):
        if self.in_cell:
            self.cell_parts.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.in_cell:
            self.row.append(" ".join("".join(self.cell_parts).split()))
            self.in_cell = False
        elif tag == "tr" and self.row:
            self.rows.append(self.row)
            self.row = []


def _parse_month(value: str) -> tuple[int, int] | None:
    normalized = re.sub(r"\s+", " ", value.strip().replace("–", "-").replace("—", "-"))
    match = re.search(r"([A-Za-z]{3,9})[-\s]+(20\d{2}|\d{2})", normalized)
    if not match:
        return None
    month_name, year_text = match.groups()
    matches = [number for name, number in _MONTHS.items() if name.startswith(month_name.lower())]
    if not matches:
        return None
    year = int(year_text)
    if year < 100:
        year += 2000
    return year, matches[0]


def _number(value: str) -> float:
    cleaned = re.sub(r"[^0-9.()-]", "", value.replace(",", ""))
    if not cleaned:
        raise ValueError(f"Not numeric: {value!r}")
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = f"-{cleaned[1:-1]}"
    return float(cleaned)


def parse_upi_product_statistics(html: str) -> tuple[UpiMonthlyRecord, ...]:
    """Parse legacy server-rendered NPCI tables without presentation classes."""
    parser = _TableParser()
    parser.feed(html)
    records: dict[tuple[int, int], UpiMonthlyRecord] = {}
    for row in parser.rows:
        period = _parse_month(row[0]) if row else None
        if period is None or len(row) < 3:
            continue
        numeric = []
        for cell in row[1:]:
            try:
                numeric.append(_number(cell))
            except ValueError:
                continue
        if len(numeric) < 2:
            continue
        banks = int(numeric[-3]) if len(numeric) >= 3 else None
        record = UpiMonthlyRecord(
            year=period[0], month=period[1], banks_live=banks,
            volume_millions=numeric[-2], value_crore=numeric[-1],
        )
        existing = records.get(period)
        if existing is not None and existing != record:
            raise ValueError(f"Conflicting NPCI rows for {period[0]}-{period[1]:02d}")
        records[period] = record
    if not records:
        raise ValueError("No monthly UPI observations found in NPCI response")
    return tuple(records[key] for key in sorted(records))


def parse_upi_api_rows(rows: list[dict]) -> tuple[UpiMonthlyRecord, ...]:
    """Parse structured rows returned by NPCI's product-statistics endpoint."""
    records: dict[tuple[int, int], UpiMonthlyRecord] = {}
    for row in rows:
        period = _parse_month(str(row.get("month", "")))
        if period is None:
            continue
        record = UpiMonthlyRecord(
            year=period[0],
            month=period[1],
            banks_live=int(_number(str(row["no_of_banks_live_on_upi"])))
            if row.get("no_of_banks_live_on_upi") not in (None, "") else None,
            volume_millions=_number(str(row["volume_in_mn"])),
            value_crore=_number(str(row["value_in_cr"])),
        )
        existing = records.get(period)
        if existing is not None and existing != record:
            raise ValueError(f"Conflicting NPCI rows for {period[0]}-{period[1]:02d}")
        records[period] = record
    return tuple(records[key] for key in sorted(records))


class NpciExtractor:
    def __init__(self, *, session: requests.Session | None = None, raw_root: str | Path = RAW_DATA_DIR / "npci") -> None:
        self.session = session or requests.Session()
        self.raw_root = Path(raw_root)

    def fetch_upi_monthly(self) -> NpciUpiResponse:
        headers = {"User-Agent": _USER_AGENT}
        tabs_response = self.session.get(
            NPCI_STATISTICS_TABS_URL,
            timeout=REQUEST_TIMEOUT,
            headers=headers,
        )
        tabs_response.raise_for_status()
        tabs_payload = tabs_response.json()
        products = tabs_payload.get("data", [{}])[0].get("products", [])
        upi = next(
            (product for product in products if str(product.get("product_name", "")).lower() == "upi"),
            None,
        )
        if upi is None:
            raise ValueError("NPCI statistics metadata does not contain UPI")
        monthly_tab = next(
            (tab for tab in upi.get("tab_details", []) if tab.get("slug") == "product-statistics-upi"),
            None,
        )
        if monthly_tab is None:
            raise ValueError("NPCI statistics metadata does not contain the UPI monthly table")

        fiscal_years = [item["year_range"] for item in monthly_tab.get("year_range", [])]
        if not fiscal_years:
            raise ValueError("NPCI UPI monthly table has no fiscal-year ranges")

        rows: list[dict] = []
        detail_payloads: list[dict] = []
        for fiscal_year in fiscal_years:
            params = {
                "product_name": "upi",
                "tab_name": monthly_tab["slug"],
                "year_range": fiscal_year,
                "excel_type": "monthly",
                "page_no": 1,
                "page_size": 100,
            }
            detail_response = self.session.get(
                NPCI_STATISTICS_DETAIL_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
                headers=headers,
            )
            detail_response.raise_for_status()
            detail_payload = detail_response.json()
            data = detail_payload.get("data") or {}
            fiscal_rows = data.get("results") or []
            if data.get("totalCount", len(fiscal_rows)) > len(fiscal_rows):
                raise ValueError(f"NPCI response for {fiscal_year} was unexpectedly paginated")
            rows.extend(fiscal_rows)
            detail_payloads.append({
                "fiscal_year": fiscal_year,
                "request_url": detail_response.url,
                "payload": detail_payload,
            })

        records = parse_upi_api_rows(rows)
        if not records:
            raise ValueError("No monthly UPI observations found in NPCI API responses")
        retrieved = datetime.now(timezone.utc)
        raw_payload = {
            "retrieved_at": retrieved.isoformat(),
            "source_url": NPCI_UPI_STATISTICS_URL,
            "metadata_request_url": tabs_response.url,
            "metadata": tabs_payload,
            "detail_responses": detail_payloads,
        }
        raw_bytes = json.dumps(raw_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        checksum = hashlib.sha256(raw_bytes).hexdigest()
        raw_payload["sha256"] = checksum
        raw_path = self.raw_root / retrieved.date().isoformat() / f"upi-monthly-api-{checksum[:12]}.json"
        if not raw_path.exists():
            write_json_atomic(raw_payload, raw_path)
        return NpciUpiResponse(
            records,
            NPCI_UPI_STATISTICS_URL,
            retrieved.isoformat(),
            raw_path,
            checksum,
        )
