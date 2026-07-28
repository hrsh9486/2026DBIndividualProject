"""Official annual gross-GST revenue extraction.

The GST portal's March report supplies exact annual totals for the two latest
fiscal years.  A Ministry of Finance/PIB release supplies the preceding
history.  Both source documents are checksum-archived before parsing.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

from config import RAW_DATA_DIR, REQUEST_TIMEOUT
from models import ObservationStatus


PIB_GST_HISTORY_URL = (
    "https://static.pib.gov.in/WriteReadData/specificdocs/documents/2024/jul/"
    "doc202471346101.pdf"
)
GST_MARCH_2025_URL = (
    "https://tutorial.gst.gov.in/downloads/news/"
    "approved_monthly_gst_data_for_publishing_mar_2025.pdf"
)
_USER_AGENT = "India-research-pipeline/1.0 (+academic research)"


@dataclass(frozen=True, slots=True)
class AnnualGrossGst:
    fiscal_start_year: int
    gross_gst_crore: float
    status: ObservationStatus
    source_url: str
    retrieved_at: str


@dataclass(frozen=True, slots=True)
class GstSourceDocument:
    name: str
    source_url: str
    retrieved_at: str
    raw_path: Path
    checksum: str


@dataclass(frozen=True, slots=True)
class GstRevenueResponse:
    observations: tuple[AnnualGrossGst, ...]
    documents: tuple[GstSourceDocument, ...]


def _normalise(text: str) -> str:
    return " ".join(text.replace("–", "-").split())


def parse_pib_gst_history_text(text: str) -> dict[int, float]:
    """Parse fiscal-year totals, reported in lakh crore, from the PIB release."""
    normalised = _normalise(text)
    patterns = {
        2020: r"fiscal year 2020-21, the total collection was ([\d.]+) lakh crores",
        2021: r"collections reaching ([\d.]+) lakh crores in 2021-22",
        2022: r"2022-23, with total collections of ([\d.]+) lakh crores",
        2023: r"fiscal year 2023-24, the GST collection has further surged to ([\d.]+) lakh crores",
    }
    output: dict[int, float] = {}
    for fiscal_year, pattern in patterns.items():
        match = re.search(pattern, normalised, flags=re.IGNORECASE)
        if match is None:
            raise ValueError(f"Could not find PIB gross-GST total for FY{fiscal_year}-{str(fiscal_year + 1)[-2:]}")
        output[fiscal_year] = float(round(float(match.group(1)) * 100_000))
    return output


def parse_gst_march_report_text(
    text: str,
    *,
    current_fiscal_start_year: int = 2024,
) -> dict[int, float]:
    """Parse previous/current fiscal-year gross totals from the March GST table."""
    normalised = _normalise(text)
    match = re.search(
        r"Total Gross GST Revenue\s+([\d,]+)\s+([\d,]+)\s+[\d.]+%\s+"
        r"([\d,]+)\s+([\d,]+)\s+[\d.]+%",
        normalised,
        flags=re.IGNORECASE,
    )
    if match is None:
        raise ValueError("Could not find Total Gross GST Revenue row in March report")
    previous_total = float(match.group(3).replace(",", ""))
    current_total = float(match.group(4).replace(",", ""))
    if previous_total <= 0 or current_total <= 0:
        raise ValueError("GST annual totals must be positive")
    return {
        current_fiscal_start_year - 1: previous_total,
        current_fiscal_start_year: current_total,
    }


class GstRevenueExtractor:
    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        raw_root: str | Path = RAW_DATA_DIR / "gst-revenue",
    ) -> None:
        self.session = session or requests.Session()
        self.raw_root = Path(raw_root)

    def _download(self, url: str, name: str) -> tuple[str, GstSourceDocument]:
        response = self.session.get(
            url,
            headers={"User-Agent": _USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        if not response.content.startswith(b"%PDF"):
            raise ValueError(f"{name} source did not return a PDF")
        retrieved = datetime.now(timezone.utc)
        checksum = hashlib.sha256(response.content).hexdigest()
        raw_path = self.raw_root / retrieved.date().isoformat() / f"{name}-{checksum[:12]}.pdf"
        if not raw_path.exists():
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(response.content)
        text = subprocess.run(
            ["pdftotext", "-layout", str(raw_path), "-"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        document = GstSourceDocument(
            name=name,
            source_url=response.url,
            retrieved_at=retrieved.isoformat(),
            raw_path=raw_path,
            checksum=checksum,
        )
        return text, document

    def fetch(self) -> GstRevenueResponse:
        history_text, history_document = self._download(PIB_GST_HISTORY_URL, "pib-gst-history")
        march_text, march_document = self._download(GST_MARCH_2025_URL, "gst-march-2025")

        history = parse_pib_gst_history_text(history_text)
        exact_latest = parse_gst_march_report_text(march_text)
        observations: dict[int, AnnualGrossGst] = {
            year: AnnualGrossGst(
                fiscal_start_year=year,
                gross_gst_crore=value,
                status=ObservationStatus.ACTUAL,
                source_url=history_document.source_url,
                retrieved_at=history_document.retrieved_at,
            )
            for year, value in history.items()
        }
        # The GST report labels the tabulated figures provisional.  It also
        # replaces the PIB release's rounded FY2023-24 total with the exact one.
        for year, value in exact_latest.items():
            observations[year] = AnnualGrossGst(
                fiscal_start_year=year,
                gross_gst_crore=value,
                status=ObservationStatus.PROVISIONAL,
                source_url=march_document.source_url,
                retrieved_at=march_document.retrieved_at,
            )
        return GstRevenueResponse(
            observations=tuple(observations[year] for year in sorted(observations)),
            documents=(history_document, march_document),
        )
