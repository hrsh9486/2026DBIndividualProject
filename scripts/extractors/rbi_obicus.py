"""RBI OBICUS manufacturing-capacity-utilisation extraction."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import requests

from config import RAW_DATA_DIR, REQUEST_TIMEOUT
from extractors.rbi_handbook import read_html_tables


OBICUS_INDEX_URL = (
    "https://www.rbi.org.in/scripts/QuarterlyPublications.aspx?"
    "head=Quarterly%20Order%20Books,%20Inventories%20and%20Capacity%20Utilisation%20Survey"
)
_USER_AGENT = "India-research-pipeline/1.0 (+academic research)"


@dataclass(frozen=True, slots=True)
class ObicusObservation:
    fiscal_start_year: int
    quarter: int
    responding_companies: int
    capacity_utilisation: float
    seasonally_adjusted_capacity_utilisation: float


@dataclass(frozen=True, slots=True)
class ObicusResponse:
    observations: tuple[ObicusObservation, ...]
    source_url: str
    retrieved_at: str
    raw_path: Path
    checksum: str


class _PublicationParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[tuple[str, str]] = []
        self._href: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((" ".join("".join(self._parts).split()), self._href))
            self._href = None
            self._parts = []


def parse_obicus_html(content: str) -> tuple[ObicusObservation, ...]:
    """Parse Table 1's unadjusted and seasonally adjusted aggregate CU values."""
    sheets = read_html_tables(content, table_label="RBI OBICUS")
    sheet = next(
        (
            candidate
            for candidate in sheets
            if candidate.rows
            and candidate.rows[0]
            and "Table 1: Capacity Utilisation" in str(candidate.rows[0][0])
        ),
        None,
    )
    if sheet is None or len(sheet.rows) < 3:
        raise ValueError("Could not find RBI OBICUS Table 1 capacity utilisation")
    header = tuple(str(value) for value in sheet.rows[1])
    required = (
        "Quarter",
        "Number of responding companies",
        "Capacity Utilisation",
        "Seasonally Adjusted Capacity Utilisation",
    )
    if header[:4] != required:
        raise ValueError(f"Unexpected RBI OBICUS Table 1 columns: {header[:4]}")

    observations: list[ObicusObservation] = []
    for row in sheet.rows[2:]:
        if len(row) < 4 or not isinstance(row[0], str):
            continue
        period = re.fullmatch(r"Q([1-4]):(20\d{2})-\d{2}", row[0])
        if period is None:
            continue
        if not all(isinstance(value, (int, float)) for value in row[1:4]):
            raise ValueError(f"Non-numeric RBI OBICUS observation: {row[:4]}")
        observation = ObicusObservation(
            fiscal_start_year=int(period.group(2)),
            quarter=int(period.group(1)),
            responding_companies=int(row[1]),
            capacity_utilisation=float(row[2]),
            seasonally_adjusted_capacity_utilisation=float(row[3]),
        )
        if not 0 <= observation.capacity_utilisation <= 100:
            raise ValueError("RBI OBICUS capacity utilisation must be between 0 and 100")
        observations.append(observation)
    keys = [(item.fiscal_start_year, item.quarter) for item in observations]
    if not observations or len(keys) != len(set(keys)):
        raise ValueError("RBI OBICUS observations are empty or duplicated")
    return tuple(sorted(observations, key=lambda item: (item.fiscal_start_year, item.quarter)))


class ObicusExtractor:
    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        raw_root: str | Path = RAW_DATA_DIR / "rbi-obicus",
    ) -> None:
        self.session = session or requests.Session()
        self.raw_root = Path(raw_root)
        self.headers = {"User-Agent": _USER_AGENT}

    def _get(self, url: str, *, referer: str | None = None):
        headers = dict(self.headers)
        if referer:
            headers["Referer"] = referer
        response = self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response

    def discover_latest(self) -> str:
        response = self._get(OBICUS_INDEX_URL)
        parser = _PublicationParser()
        parser.feed(response.text)
        for label, href in parser.anchors:
            if "order books, inventories and capacity utilisation survey" in label.lower():
                if "PublicationsView.aspx?id=" in href:
                    return urljoin(response.url, href)
        # Some RBI index vintages use terse anchor text; retain a structural fallback.
        for _, href in parser.anchors:
            if "PublicationsView.aspx?id=" in href:
                return urljoin(response.url, href)
        raise ValueError("RBI OBICUS index contains no publication link")

    def fetch(self) -> ObicusResponse:
        source_url = self.discover_latest()
        response = self._get(source_url, referer=OBICUS_INDEX_URL)
        retrieved = datetime.now(timezone.utc)
        checksum = hashlib.sha256(response.content).hexdigest()
        publication_id = re.search(r"id=(\d+)", response.url)
        name = publication_id.group(1) if publication_id else checksum[:12]
        raw_path = self.raw_root / retrieved.date().isoformat() / f"obicus-{name}-{checksum[:12]}.html"
        if not raw_path.exists():
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(response.content)
        return ObicusResponse(
            observations=parse_obicus_html(response.text),
            source_url=response.url,
            retrieved_at=retrieved.isoformat(),
            raw_path=raw_path,
            checksum=checksum,
        )
