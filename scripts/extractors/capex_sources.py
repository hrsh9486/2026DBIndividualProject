"""Source acquisition for the CapEx pipeline; no transformation or publication."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

import pandas as pd

from config import RAW_DATA_DIR
from config.capex_analysis import ANALYSIS_START, CAPEX_MARKETS, CORPORATE_CASES
from extractors.corporate_fundamentals import CorporateFundamentalsExtractor
from extractors.delivery_reference import extract_delivery_sources
from extractors.national_accounts import NationalAccountsExtractor, parse_national_accounts_pdf_text
from extractors.nifty_indices import NiftyIndicesExtractor
from extractors.rbi_handbook import RbiHandbookExtractor, read_html_tables
from extractors.rbi_obicus import ObicusExtractor, parse_obicus_html
from extractors.union_budget import UnionBudgetExtractor, parse_expenditure_pdf_text
from models.capex_sources import (
    AnalysisSources,
    CapexSources,
    CorporateFundamental,
    DepthSources,
    NationalAccountsResponse,
    ObicusResponse,
    RbiHandbookResponse,
    StructuralSources,
)


def acquire_structural_sources(
    raw_root: str | Path = RAW_DATA_DIR,
    *,
    start_edition: int = 2018,
) -> StructuralSources:
    raw_root = Path(raw_root)
    rbi = RbiHandbookExtractor(raw_root=raw_root / "rbi-handbook")
    return StructuralSources(
        budget_snapshots=UnionBudgetExtractor(
            raw_root=raw_root / "union-budget"
        ).fetch_expenditure_snapshots(start_edition),
        nominal_gdp=rbi.fetch_publication(
            23175,
            table_number=1,
            table_label="Table 1 : Macro-Economic Aggregates (Base Year: 2011-12 At Current Prices)",
        ),
        national_accounts=NationalAccountsExtractor(
            raw_root=raw_root / "mospi-national-accounts"
        ).fetch(),
        obicus=ObicusExtractor(
            raw_root=raw_root / "rbi-obicus"
        ).fetch_publication(23808),
        debt=rbi.fetch_publication(
            23413,
            table_number=239,
            table_label="Table 239 : Select Debt Indicators of Central and State Governments (As Percentage to GDP)",
        ),
        fiscal=rbi.fetch_publication(
            23410,
            table_number=236,
            table_label="Table 236 : Select Fiscal Indicators of the Central Government (As Percentage to GDP)",
        ),
    )


def acquire_analysis_sources(
    raw_root: str | Path = RAW_DATA_DIR,
    *,
    prices_json: str | Path | None = None,
    include_corporate: bool = True,
) -> AnalysisSources:
    raw_root = Path(raw_root)
    if prices_json is not None:
        raw = json.loads(Path(prices_json).read_text(encoding="utf-8"))
        prices = pd.DataFrame(raw["values"], index=pd.to_datetime(raw["dates"]))
    else:
        prices = NiftyIndicesExtractor(
            raw_root=raw_root / "nifty-indices"
        ).fetch_total_return_indices(
            {market.key: market.ticker for market in CAPEX_MARKETS},
            start_year=2018,
        )
    prices.index = pd.to_datetime(prices.index)
    prices = prices.loc[pd.Timestamp(ANALYSIS_START):]
    corporate_records = (
        CorporateFundamentalsExtractor(
            raw_root=raw_root / "corporate-fundamentals"
        ).fetch(CORPORATE_CASES)
        if include_corporate
        else ()
    )
    return AnalysisSources(prices=prices, corporate_records=corporate_records)


def acquire_depth_sources(raw_root: str | Path = RAW_DATA_DIR) -> DepthSources:
    extractor = RbiHandbookExtractor(raw_root=Path(raw_root) / "rbi-handbook")
    return DepthSources(
        project_status=extractor.fetch_publication(
            21841,
            table_number=35,
            table_label="RBI Handbook 2022-23, Table 35 — Implementation of Central Sector Projects",
        ),
        project_cost=extractor.fetch_publication(
            21842,
            table_number=36,
            table_label="RBI Handbook 2022-23, Table 36 — Cost Overrun of Delayed Central Sector Projects",
        ),
        current_gsdp=extractor.fetch_publication(
            23470,
            table_number=21,
            table_label="RBI Handbook of Statistics on Indian States, Table 21 — GSDP at Current Prices",
        ),
        constant_gsdp=extractor.fetch_publication(
            23471,
            table_number=22,
            table_label="RBI Handbook of Statistics on Indian States, Table 22 — GSDP at Constant Prices",
        ),
        capital_outlay=extractor.fetch_publication(
            23623,
            table_number=174,
            table_label="RBI Handbook of Statistics on Indian States, Table 174 — State-wise Capital Outlay",
        ),
    )


def acquire_capex_sources(
    raw_root: str | Path = RAW_DATA_DIR,
    *,
    start_edition: int = 2018,
    prices_json: str | Path | None = None,
) -> CapexSources:
    """Acquire every source required for a complete thirteen-artifact run."""
    return CapexSources(
        structural=acquire_structural_sources(raw_root, start_edition=start_edition),
        analysis=acquire_analysis_sources(raw_root, prices_json=prices_json),
        depth=acquire_depth_sources(raw_root),
        delivery=extract_delivery_sources(),
    )


def _latest(root: Path, pattern: str) -> Path:
    candidates = list(root.glob(pattern))
    if not candidates:
        raise FileNotFoundError(f"No landed source matches {root / pattern}")
    latest = candidates[0]
    latest_key = (latest.parent.name, latest.stat().st_mtime_ns, latest.name)
    for candidate in candidates[1:]:
        candidate_key = (
            candidate.parent.name,
            candidate.stat().st_mtime_ns,
            candidate.name,
        )
        if candidate_key > latest_key:
            latest = candidate
            latest_key = candidate_key
    return latest


def _retrieved_at(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def _landed_rbi_response(
    raw_root: Path,
    filename: str,
    *,
    table_number: int,
    table_label: str,
    publication_id: int,
) -> RbiHandbookResponse:
    source = _latest(raw_root / "rbi-handbook", f"**/{filename}")
    content = source.read_bytes()
    return RbiHandbookResponse(
        table_number=table_number,
        table_label=table_label,
        sheets=read_html_tables(content.decode("utf-8"), table_label=table_label),
        source_url=f"https://www.rbi.org.in/scripts/PublicationsView.aspx?id={publication_id}",
        retrieved_at=_retrieved_at(source),
        raw_path=source,
        checksum=hashlib.sha256(content).hexdigest(),
    )


def load_landed_capex_sources(
    raw_root: str | Path,
    *,
    start_edition: int = 2018,
) -> CapexSources:
    """Replay immutable landed files through the production parsers without network I/O."""
    raw_root = Path(raw_root)

    snapshots = []
    for fiscal_dir in sorted((raw_root / "union-budget").glob("FY*")):
        edition = int(fiscal_dir.name[2:6])
        if edition < start_edition:
            continue
        source = _latest(fiscal_dir, "budget-at-a-glance-expenditure-*.pdf")
        content = source.read_bytes()
        text = subprocess.run(
            ["pdftotext", "-layout", str(source), "-"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        snapshots.append(parse_expenditure_pdf_text(
            text,
            edition_start_year=edition,
            source_url=(
                "https://www.indiabudget.gov.in/budget2018-2019/ub2018-19/bag/bag6.pdf"
                if edition == 2018
                else "https://www.indiabudget.gov.in/doc/Budget_at_Glance/bag6.pdf"
                if edition == 2026
                else f"https://www.indiabudget.gov.in/budget{edition}-{str(edition + 1)[-2:]}/doc/Budget_at_Glance/bag6.pdf"
            ),
            retrieved_at=_retrieved_at(source),
            raw_path=source,
            checksum=hashlib.sha256(content).hexdigest(),
        ))

    nominal_gdp = _landed_rbi_response(
        raw_root,
        "publication-23175-*.html",
        table_number=1,
        table_label="Table 1 : Macro-Economic Aggregates (Base Year: 2011-12 At Current Prices)",
        publication_id=23175,
    )
    debt = _landed_rbi_response(
        raw_root,
        "publication-23413-*.html",
        table_number=239,
        table_label="Table 239 : Select Debt Indicators of Central and State Governments (As Percentage to GDP)",
        publication_id=23413,
    )
    fiscal = _landed_rbi_response(
        raw_root,
        "publication-23410-*.html",
        table_number=236,
        table_label="Table 236 : Select Fiscal Indicators of the Central Government (As Percentage to GDP)",
        publication_id=23410,
    )

    national_source = _latest(raw_root / "mospi-national-accounts", "**/national-accounts-*.pdf")
    national_content = national_source.read_bytes()
    national_text = subprocess.run(
        ["pdftotext", "-layout", str(national_source), "-"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    national_accounts = NationalAccountsResponse(
        observations=parse_national_accounts_pdf_text(national_text),
        source_url="https://mospi.gov.in/uploads/release_calendar/1772190058170_Press_Note_on_New_Series_of_GDP_Estimates_with_Base_Year_2022-23_27022026.pdf",
        retrieved_at=_retrieved_at(national_source),
        raw_path=national_source,
        checksum=hashlib.sha256(national_content).hexdigest(),
    )

    obicus_source = _latest(raw_root / "rbi-obicus", "**/obicus-*.html")
    obicus_content = obicus_source.read_bytes()
    obicus = ObicusResponse(
        observations=parse_obicus_html(obicus_content.decode("utf-8")),
        source_url="https://www.rbi.org.in/scripts/PublicationsView.aspx?id=23808",
        retrieved_at=_retrieved_at(obicus_source),
        raw_path=obicus_source,
        checksum=hashlib.sha256(obicus_content).hexdigest(),
    )

    price_columns = {}
    for market in CAPEX_MARKETS:
        source = _latest(raw_root / "nifty-indices", f"**/{market.key}-*.json")
        payload = json.loads(source.read_text(encoding="utf-8"))
        price_columns[market.key] = pd.Series({
            pd.Timestamp(row["date"]): float(row["tri"])
            for row in payload["observations"]
        })
    prices = pd.DataFrame(price_columns).sort_index()
    prices = prices.loc[pd.Timestamp(ANALYSIS_START):]

    cases = {case.key: case for case in CORPORATE_CASES}
    corporate_records = []
    for key, case in cases.items():
        source = _latest(raw_root / "corporate-fundamentals", f"**/{key}-*.json")
        payload = json.loads(source.read_text(encoding="utf-8"))
        corporate_records.extend(
            CorporateFundamental(
                key,
                case.label,
                case.group,
                pd.Timestamp(row["fiscal_end"]),
                row.get("revenue"),
                row.get("ebitda"),
                row.get("capex"),
                row.get("net_ppe"),
                row.get("debt"),
                row.get("roce_proxy"),
            )
            for row in payload["observations"]
        )

    depth = DepthSources(
        project_status=_landed_rbi_response(
            raw_root, "publication-21841-*.html",
            table_number=35,
            table_label="RBI Handbook 2022-23, Table 35 — Implementation of Central Sector Projects",
            publication_id=21841,
        ),
        project_cost=_landed_rbi_response(
            raw_root, "publication-21842-*.html",
            table_number=36,
            table_label="RBI Handbook 2022-23, Table 36 — Cost Overrun of Delayed Central Sector Projects",
            publication_id=21842,
        ),
        current_gsdp=_landed_rbi_response(
            raw_root, "publication-23470-*.html",
            table_number=21,
            table_label="RBI Handbook of Statistics on Indian States, Table 21 — GSDP at Current Prices",
            publication_id=23470,
        ),
        constant_gsdp=_landed_rbi_response(
            raw_root, "publication-23471-*.html",
            table_number=22,
            table_label="RBI Handbook of Statistics on Indian States, Table 22 — GSDP at Constant Prices",
            publication_id=23471,
        ),
        capital_outlay=_landed_rbi_response(
            raw_root, "publication-23623-*.html",
            table_number=174,
            table_label="RBI Handbook of Statistics on Indian States, Table 174 — State-wise Capital Outlay",
            publication_id=23623,
        ),
    )
    return CapexSources(
        structural=StructuralSources(
            budget_snapshots=tuple(snapshots),
            nominal_gdp=nominal_gdp,
            national_accounts=national_accounts,
            obicus=obicus,
            debt=debt,
            fiscal=fiscal,
        ),
        analysis=AnalysisSources(
            prices=prices,
            corporate_records=tuple(corporate_records),
        ),
        depth=depth,
        delivery=extract_delivery_sources(),
    )
