"""Corporate annual-statement extraction for the frozen CapEx case-study basket."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

from config import RAW_DATA_DIR
from config.capex_analysis import CorporateCase
from exporters import write_json_atomic


@dataclass(frozen=True, slots=True)
class CorporateFundamental:
    company_key: str
    company_label: str
    group: str
    fiscal_end: pd.Timestamp
    revenue: float | None
    ebitda: float | None
    capex: float | None
    net_ppe: float | None
    debt: float | None
    roce_proxy: float | None


def _value(statement: pd.DataFrame, column, *labels: str) -> float | None:
    for label in labels:
        if label in statement.index:
            value = statement.at[label, column]
            if pd.notna(value):
                return float(value)
    return None


class CorporateFundamentalsExtractor:
    def __init__(self, *, raw_root: str | Path = RAW_DATA_DIR / "corporate-fundamentals") -> None:
        self.raw_root = Path(raw_root)

    def fetch(self, cases: tuple[CorporateCase, ...]) -> tuple[CorporateFundamental, ...]:
        retrieved = datetime.now(timezone.utc)
        output = []
        for case in cases:
            ticker = yf.Ticker(case.ticker)
            income = ticker.financials
            balance = ticker.balance_sheet
            cashflow = ticker.cashflow
            columns = sorted(set(income.columns) | set(balance.columns) | set(cashflow.columns))
            landed = []
            for column in columns:
                revenue = _value(income, column, "Total Revenue")
                ebitda = _value(income, column, "EBITDA", "Normalized EBITDA", "Operating Income")
                capex = _value(cashflow, column, "Capital Expenditure", "Capital Expenditure Reported")
                net_ppe = _value(balance, column, "Net PPE", "Gross PPE")
                debt = _value(balance, column, "Total Debt")
                ebit = _value(income, column, "EBIT", "Operating Income")
                assets = _value(balance, column, "Total Assets")
                current_liabilities = _value(balance, column, "Current Liabilities", "Total Current Liabilities")
                capital_employed = (
                    assets - current_liabilities
                    if assets is not None and current_liabilities is not None
                    else None
                )
                roce = (
                    ebit / capital_employed * 100
                    if ebit is not None and capital_employed not in (None, 0)
                    else None
                )
                record = CorporateFundamental(
                    case.key, case.label, case.group, pd.Timestamp(column),
                    revenue, ebitda, abs(capex) if capex is not None else None,
                    net_ppe, debt, roce,
                )
                if any(value is not None for value in (revenue, ebitda, capex, net_ppe, debt)):
                    output.append(record)
                    landed.append({
                        "fiscal_end": record.fiscal_end.strftime("%Y-%m-%d"),
                        "revenue": revenue,
                        "ebitda": ebitda,
                        "capex": record.capex,
                        "net_ppe": net_ppe,
                        "debt": debt,
                        "roce_proxy": roce,
                    })
            self._land(case, landed, retrieved)
        if not output:
            raise RuntimeError("No corporate fundamentals were returned")
        return tuple(output)

    def _land(self, case: CorporateCase, observations: list[dict], retrieved: datetime) -> Path:
        checksum = hashlib.sha256(
            json.dumps(observations, sort_keys=True, allow_nan=False).encode("utf-8")
        ).hexdigest()
        payload = {
            "retrieved_at": retrieved.isoformat(),
            "source_url": f"https://finance.yahoo.com/quote/{case.ticker}/financials",
            "company": case.label,
            "ticker": case.ticker,
            "group": case.group,
            "observations": observations,
            "sha256": checksum,
        }
        path = self.raw_root / retrieved.date().isoformat() / f"{case.key}-{checksum[:12]}.json"
        if not path.exists():
            write_json_atomic(payload, path)
        return path
