"""Official AISHE and PLFS extraction for the human-capital lens."""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests

from config import RAW_DATA_DIR, REQUEST_TIMEOUT


AISHE_REPORT_URL = (
    "https://cdnbbsr.s3waas.gov.in/"
    "s392049debbe566ca5782a3045cf300a3c/uploads/2026/07/202607131602421770.pdf"
)
PLFS_REPORT_URL = (
    "https://www.mospi.gov.in/uploads/publications_reports/"
    "publications_reports1780040415321_0624fb13-fb47-40bc-b470-7c7e9635c3ef_"
    "PLFS_2025_F_REV_29052026.pdf"
)
_USER_AGENT = "India-research-pipeline/1.0 (+academic research)"
_NUMBER = r"-?\d+(?:\.\d+)?"


@dataclass(frozen=True, slots=True)
class AnnualValue:
    year: int
    value: float


@dataclass(frozen=True, slots=True)
class HumanCapitalSourceResponse:
    values: tuple[AnnualValue, ...]
    source_url: str
    retrieved_at: str
    raw_path: Path
    checksum: str


def _normalise(text: str) -> str:
    return " ".join(text.replace("–", "-").split())


def parse_aishe_ger_pdf_text(text: str) -> tuple[AnnualValue, ...]:
    """Parse the All-India, all-category, both-sex GER trend in Table 47."""
    normalised = _normalise(text)
    start = normalised.find("Table 47. Gross Enrollment Ratio (GER) Trends Over the Last 5 Years")
    if start < 0:
        raise ValueError("Could not find AISHE Table 47 GER trend")
    section = normalised[start:start + 8_000]
    rows = re.findall(
        rf"(20\d{{2}})-(\d{{2}})\s+({_NUMBER})\s+({_NUMBER})\s+({_NUMBER})"
        rf"\s+({_NUMBER})\s+({_NUMBER})\s+({_NUMBER})\s+({_NUMBER})\s+({_NUMBER})\s+({_NUMBER})",
        section,
    )
    if len(rows) < 5:
        raise ValueError("Could not find five All-India AISHE GER rows")
    # The first state block in Table 47 is All India. Columns 1-3 are male,
    # female and both sexes for all social categories.
    values = tuple(AnnualValue(int(row[0]), float(row[4])) for row in rows[:5])
    if len({item.year for item in values}) != 5:
        raise ValueError("AISHE GER years were not unique")
    return tuple(sorted(values, key=lambda item: item.year))


def _plfs_year_blocks(section: str) -> dict[int, str]:
    matches = list(re.finditer(r"PLFS\s+(20\d{2})", section))
    return {
        int(match.group(1)): section[match.end():matches[index + 1].start() if index + 1 < len(matches) else len(section)]
        for index, match in enumerate(matches)
    }


def parse_plfs_regular_salaried_pdf_text(text: str) -> tuple[AnnualValue, ...]:
    """Parse rural+urban persons' regular wage/salaried share from Statement 7."""
    normalised = _normalise(text)
    start = normalised.find("Statement 7: Percentage distribution of workers")
    end = normalised.find("2025 refers to the period", start)
    if start < 0 or end < 0:
        raise ValueError("Could not find PLFS Statement 7")
    output = []
    for year, block in _plfs_year_blocks(normalised[start:end]).items():
        combined = re.search(r"rural\s*\+\s*urban(.*)", block)
        if combined is None:
            raise ValueError(f"Could not find PLFS rural+urban block for {year}")
        person = re.search(
            rf"person\s+({_NUMBER})\s+({_NUMBER})\s+({_NUMBER})\s+({_NUMBER})\s+({_NUMBER})\s+({_NUMBER})",
            combined.group(1),
        )
        if person is None:
            raise ValueError(f"Could not find PLFS combined persons employment row for {year}")
        output.append(AnnualValue(year, float(person.group(4))))
    if len(output) < 4:
        raise ValueError("PLFS Statement 7 did not contain the expected four-year trend")
    return tuple(sorted(output, key=lambda item: item.year))


def parse_plfs_educated_unemployment_pdf_text(text: str) -> tuple[AnnualValue, ...]:
    """Parse the published 15+ secondary-and-above unemployment trend."""
    normalised = _normalise(text)
    start = normalised.find("Statement 17: Unemployment rates")
    end = normalised.find("2025 refers to the period", start)
    if start < 0 or end < 0:
        raise ValueError("Could not find PLFS Statement 17")
    output = []
    for year, block in _plfs_year_blocks(normalised[start:end]).items():
        row = re.search(
            rf"secondary\s*&\s*above\s+({_NUMBER})\s+({_NUMBER})\s+({_NUMBER})\s+"
            rf"({_NUMBER})\s+({_NUMBER})\s+({_NUMBER})\s+({_NUMBER})\s+({_NUMBER})\s+({_NUMBER})",
            block,
        )
        if row is None:
            raise ValueError(f"Could not find PLFS educated-unemployment row for {year}")
        output.append(AnnualValue(year, float(row.group(9))))
    if len(output) < 4:
        raise ValueError("PLFS Statement 17 did not contain the expected four-year trend")
    return tuple(sorted(output, key=lambda item: item.year))


class HumanCapitalExtractor:
    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        raw_root: str | Path = RAW_DATA_DIR / "human-capital",
    ) -> None:
        self.session = session or requests.Session()
        self.raw_root = Path(raw_root)

    def _download(self, url: str, name: str) -> tuple[str, str, str, Path, str]:
        response = self.session.get(
            url,
            headers={"User-Agent": _USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        if not response.content.startswith(b"%PDF"):
            raise ValueError(f"{name} source did not return a PDF")
        retrieved_at = datetime.now(timezone.utc).isoformat()
        checksum = hashlib.sha256(response.content).hexdigest()
        raw_path = self.raw_root / retrieved_at[:10] / f"{name}-{checksum[:12]}.pdf"
        if not raw_path.exists():
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(response.content)
        text = subprocess.run(
            ["pdftotext", "-layout", str(raw_path), "-"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        return text, response.url, retrieved_at, raw_path, checksum

    def fetch_aishe_ger(self) -> HumanCapitalSourceResponse:
        text, source_url, retrieved_at, raw_path, checksum = self._download(AISHE_REPORT_URL, "aishe-2023-24")
        return HumanCapitalSourceResponse(
            parse_aishe_ger_pdf_text(text), source_url, retrieved_at, raw_path, checksum,
        )

    def fetch_plfs_regular_salaried(self) -> HumanCapitalSourceResponse:
        text, source_url, retrieved_at, raw_path, checksum = self._download(PLFS_REPORT_URL, "plfs-2025")
        return HumanCapitalSourceResponse(
            parse_plfs_regular_salaried_pdf_text(text), source_url, retrieved_at, raw_path, checksum,
        )

    def fetch_plfs_educated_unemployment(self) -> HumanCapitalSourceResponse:
        text, source_url, retrieved_at, raw_path, checksum = self._download(PLFS_REPORT_URL, "plfs-2025")
        return HumanCapitalSourceResponse(
            parse_plfs_educated_unemployment_pdf_text(text), source_url, retrieved_at, raw_path, checksum,
        )

    def fetch_plfs(self) -> tuple[HumanCapitalSourceResponse, HumanCapitalSourceResponse]:
        """Download PLFS once and return unemployment and salaried responses."""
        text, source_url, retrieved_at, raw_path, checksum = self._download(PLFS_REPORT_URL, "plfs-2025")
        provenance = (source_url, retrieved_at, raw_path, checksum)
        return (
            HumanCapitalSourceResponse(parse_plfs_educated_unemployment_pdf_text(text), *provenance),
            HumanCapitalSourceResponse(parse_plfs_regular_salaried_pdf_text(text), *provenance),
        )
