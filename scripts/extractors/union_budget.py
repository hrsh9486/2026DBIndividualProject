"""Union Budget expenditure extraction from authoritative annual PDFs."""

from __future__ import annotations

import hashlib
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests

from config import RAW_DATA_DIR, REQUEST_TIMEOUT
from models.capex_sources import UnionBudgetSnapshot


BUDGET_ROOT = "https://www.indiabudget.gov.in/"
_USER_AGENT = "India-research-pipeline/1.0 (+academic research)"


def _amount(value: str) -> float:
    return float(value.replace(",", ""))


def _four_amounts(text: str, label: str) -> tuple[float, float, float, float]:
    normalized = re.sub(r"[ \t]+", " ", text)
    pattern = (
        rf"{re.escape(label)}(?:\d+|\*+)?\s+"
        r"([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)"
    )
    match = re.search(pattern, normalized, flags=re.IGNORECASE)
    if match is None:
        raise ValueError(f"Could not find four-column Union Budget row: {label}")
    return tuple(_amount(value) for value in match.groups())


def _four_amounts_for_any(text: str, labels: tuple[str, ...]) -> tuple[float, float, float, float]:
    for label in labels:
        try:
            return _four_amounts(text, label)
        except ValueError:
            continue
    raise ValueError(f"Could not find any Union Budget row: {', '.join(labels)}")


def parse_expenditure_pdf_text(
    text: str,
    *,
    edition_start_year: int,
    source_url: str,
    retrieved_at: str,
    raw_path: Path,
    checksum: str,
) -> UnionBudgetSnapshot:
    """Parse the first-page expenditure table after pdftotext layout extraction."""
    expected_start_years = {edition_start_year - 2, edition_start_year - 1, edition_start_year}
    observed_start_years = {
        int(value) for value in re.findall(r"\b(20\d{2})-(?:20)?\d{2}\b", text)
    }
    if not expected_start_years.issubset(observed_start_years):
        raise ValueError(f"Union Budget edition {edition_start_year} has unexpected fiscal-year headers")
    # Older Budget-at-a-Glance editions put budgetary capital expenditure on
    # the "Gross Budgetary Support" row beneath a broader capital-investment
    # table that also includes public-enterprise IEBR.
    capex = _four_amounts_for_any(text, ("Capital Expenditure", "Gross Budgetary Support"))
    total = _four_amounts(text, "Grand Total")
    if any(value <= 0 for value in (*capex, *total)):
        raise ValueError("Union Budget expenditure values must be positive")
    if any(capital > expenditure for capital, expenditure in zip(capex, total)):
        raise ValueError("Capital expenditure cannot exceed total expenditure")
    return UnionBudgetSnapshot(
        edition_start_year=edition_start_year,
        actual_capex=capex[0],
        prior_budget_capex=capex[1],
        prior_revised_capex=capex[2],
        current_budget_capex=capex[3],
        actual_total_expenditure=total[0],
        prior_budget_total_expenditure=total[1],
        prior_revised_total_expenditure=total[2],
        current_budget_total_expenditure=total[3],
        source_url=source_url,
        retrieved_at=retrieved_at,
        raw_path=raw_path,
        checksum=checksum,
    )


class UnionBudgetExtractor:
    def __init__(self, *, session: requests.Session | None = None, raw_root: str | Path = RAW_DATA_DIR / "union-budget") -> None:
        self.session = session or requests.Session()
        self.raw_root = Path(raw_root)
        self.headers = {"User-Agent": _USER_AGENT}

    def _get(self, url: str):
        response = self.session.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response

    def current_edition_start_year(self) -> int:
        response = self._get(BUDGET_ROOT)
        match = re.search(r"Union Budget Documents\s+(20\d{2})-(?:20)?\d{2}", response.text)
        if match is None:
            raise ValueError("Could not determine the current Union Budget edition")
        return int(match.group(1))

    def _edition_roots(self, edition_start_year: int, current_start_year: int) -> tuple[str, ...]:
        """Return known official archive URL conventions, newest first."""
        if edition_start_year == current_start_year:
            return (BUDGET_ROOT,)
        short_year = str(edition_start_year + 1)[-2:]
        return (
            urljoin(BUDGET_ROOT, f"budget{edition_start_year}-{short_year}/"),
            urljoin(BUDGET_ROOT, f"budget{edition_start_year}-{edition_start_year + 1}/"),
        )

    def fetch_expenditure_snapshot(
        self,
        edition_start_year: int,
        *,
        current_start_year: int,
    ) -> UnionBudgetSnapshot:
        attempted_roots: list[str] = []
        edition_root = ""
        matches: list[str] = []
        for candidate in self._edition_roots(edition_start_year, current_start_year):
            attempted_roots.append(candidate)
            try:
                index_response = self._get(candidate)
            except requests.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 404:
                    continue
                raise
            candidate_matches = re.findall(
                r"href=[\"']([^\"']*bag6\.pdf)[\"']",
                index_response.text,
                flags=re.IGNORECASE,
            )
            if not candidate_matches:
                glance_pages = re.findall(
                    r"href=[\"']([^\"']*glance[^\"']*)[\"']",
                    index_response.text,
                    flags=re.IGNORECASE,
                )
                if not glance_pages and edition_start_year <= 2018:
                    glance_pages = ["glance.asp"]
                for glance_page in glance_pages:
                    glance_response = self._get(urljoin(candidate, glance_page))
                    candidate_matches = re.findall(
                        r"href=[\"']([^\"']*bag6\.pdf)[\"']",
                        glance_response.text,
                        flags=re.IGNORECASE,
                    )
                    if candidate_matches:
                        break
            if candidate_matches:
                edition_root = candidate
                matches = candidate_matches
                break
        if not matches:
            raise ValueError(
                f"Budget {edition_start_year} has no expenditure PDF link at: "
                + ", ".join(attempted_roots)
            )
        source_url = urljoin(edition_root, matches[0])
        pdf_response = self._get(source_url)
        checksum = hashlib.sha256(pdf_response.content).hexdigest()
        raw_path = (
            self.raw_root
            / f"FY{edition_start_year}-{str(edition_start_year + 1)[-2:]}"
            / f"budget-at-a-glance-expenditure-{checksum[:12]}.pdf"
        )
        if not raw_path.exists():
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(pdf_response.content)
        converted = subprocess.run(
            ["pdftotext", "-layout", str(raw_path), "-"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        retrieved_at = datetime.now(timezone.utc).isoformat()
        return parse_expenditure_pdf_text(
            converted,
            edition_start_year=edition_start_year,
            source_url=source_url,
            retrieved_at=retrieved_at,
            raw_path=raw_path,
            checksum=checksum,
        )

    def fetch_expenditure_snapshots(self, start_edition: int = 2018) -> tuple[UnionBudgetSnapshot, ...]:
        current = self.current_edition_start_year()
        if start_edition > current:
            raise ValueError("Start edition is after the current Union Budget")
        return tuple(
            self.fetch_expenditure_snapshot(year, current_start_year=current)
            for year in range(start_edition, current + 1)
        )
