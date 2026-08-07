"""MoSPI national-accounts extraction for institutional fixed investment."""

from __future__ import annotations

import hashlib
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests

from config import RAW_DATA_DIR, REQUEST_TIMEOUT
from models.capex_sources import NationalAccountsObservation, NationalAccountsResponse


NATIONAL_ACCOUNTS_RELEASE_URLS = (
    # MoSPI publishes the same release under its release calendar and latest-release
    # routes.  The latter intermittently rejects non-browser clients with HTTP 403.
    "https://mospi.gov.in/uploads/release_calendar/"
    "1772190058170_Press_Note_on_New_Series_of_GDP_Estimates_with_Base_Year_2022-23_27022026.pdf",
    "https://mospi.gov.in/uploads/latestReleases/"
    "latest_release_1772189865181_f040336d-bc57-4aed-b80f-586d9ccb279e_"
    "Press_Note_on_New_Series_of_GDP_Estimates_with_Base_Year_2022-23_27022026.pdf",
)
_USER_AGENT = "India-research-pipeline/1.0 (+academic research)"


def _section(text: str, start: str, end: str) -> str:
    match = re.search(rf"{re.escape(start)}(.*?){re.escape(end)}", text, flags=re.DOTALL)
    if match is None:
        raise ValueError(f"Could not find MoSPI statement section {start}")
    return " ".join(match.group(1).split())


def _three_amounts(text: str, *labels: str) -> tuple[float, float, float]:
    for label in labels:
        match = re.search(
            rf"{re.escape(label)}\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)",
            text,
            flags=re.IGNORECASE,
        )
        if match is not None:
            return tuple(float(value.replace(",", "")) for value in match.groups())
    raise ValueError(f"Could not find MoSPI row matching: {', '.join(labels)}")


def parse_national_accounts_pdf_text(text: str) -> tuple[NationalAccountsObservation, ...]:
    current_prices = _section(text, "Statement 1.1 B", "Statement 1.2 B")
    investment = _section(text, "Statement 7.1 B", "Statement 7.2 B")
    years_match = re.search(r"S\.No\.\s+Item\s+(20\d{2})-\d{2}\s+(20\d{2})-\d{2}\s+(20\d{2})-\d{2}", investment)
    if years_match is None:
        raise ValueError("Could not find MoSPI GFCF fiscal-year headers")
    years = tuple(int(value) for value in years_match.groups())
    gdp = _three_amounts(current_prices, "GDP (1+2-3)", "Gross Domestic Product (GDP)")
    total = _three_amounts(investment, "Gross Fixed Capital Formation")
    private_non_financial = _three_amounts(investment, "2 Private non-financial corporations")
    private_financial = _three_amounts(investment, "4 Private financial corporations")
    observations = tuple(
        NationalAccountsObservation(year, gdp[index], total[index], private_non_financial[index] + private_financial[index])
        for index, year in enumerate(years)
    )
    if any(item.private_corporate_gfcf_crore > item.total_gfcf_crore for item in observations):
        raise ValueError("Private corporate GFCF cannot exceed total GFCF")
    return observations


class NationalAccountsExtractor:
    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        raw_root: str | Path = RAW_DATA_DIR / "mospi-national-accounts",
    ) -> None:
        self.session = session or requests.Session()
        self.raw_root = Path(raw_root)

    def fetch(self) -> NationalAccountsResponse:
        response = None
        failures: list[str] = []
        for source_url in NATIONAL_ACCOUNTS_RELEASE_URLS:
            candidate = self.session.get(
                source_url,
                headers={"User-Agent": _USER_AGENT, "Referer": "https://mospi.gov.in/"},
                timeout=REQUEST_TIMEOUT,
            )
            if candidate.ok:
                response = candidate
                break
            failures.append(f"{candidate.status_code} {source_url}")
        if response is None:
            raise RuntimeError("MoSPI national-accounts download failed: " + "; ".join(failures))
        if not response.content.startswith(b"%PDF"):
            raise ValueError("MoSPI national-accounts release did not return a PDF")
        retrieved = datetime.now(timezone.utc)
        checksum = hashlib.sha256(response.content).hexdigest()
        raw_path = self.raw_root / retrieved.date().isoformat() / f"national-accounts-{checksum[:12]}.pdf"
        if not raw_path.exists():
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(response.content)
        text = subprocess.run(
            ["pdftotext", "-layout", str(raw_path), "-"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        return NationalAccountsResponse(
            observations=parse_national_accounts_pdf_text(text),
            source_url=response.url,
            retrieved_at=retrieved.isoformat(),
            raw_path=raw_path,
            checksum=checksum,
        )
