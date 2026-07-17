"""
government_spending_analysis.py

Bucket 05: Government Spending
Pulls India (+ peer) government spending indicators from the World Bank API
(no key required) and writes structured JSON outputs for the frontend
dashboard, following the same main()/helper.write_json pattern used by
inr_currency_analysis.py.

Some categories the framework calls for -- space (ISRO/DoS budget) and
manufacturing incentive spending (PLI schemes) -- have no public API source
and are only available via manual pulls from Union Budget documents. Those
are written out as flagged placeholders rather than silently omitted, in
keeping with the "RBI DBIE = manual pull" precedent from the macro bucket.

Requires: requests, pandas, and a local `helper` module exposing
  - helper.write_json(obj, filename, output_dir)
  - helper.clean_float(value, decimals)
  - helper.metadata(extra=None)

Run:
    python government_spending_analysis.py
"""

import os

import pandas as pd
import requests

import helper
from config import OUTPUT_DIR, WB_BASE, REQUEST_TIMEOUT, RETRY_ATTEMPTS, RETRY_BACKOFF_SECONDS, START_YEAR, COUNTRY_CODE, PEER_CODES

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------





END_YEAR = pd.Timestamp.now().year
# World Bank indicator codes for this bucket
INDICATORS = {
    "total_expense_pct_gdp": "GC.XPN.TOTL.GD.ZS",        # General government total expense (% of GDP)
    "defence_pct_gdp": "MS.MIL.XPND.GD.ZS",               # Military expenditure (% of GDP)
    "defence_pct_govt_exp": "MS.MIL.XPND.ZS",             # Military expenditure (% of general govt expenditure)
    "health_pct_gdp": "SH.XPD.GHED.GD.ZS",                # Domestic general government health expenditure (% of GDP)
    "exports_pct_gdp": "NE.EXP.GNFS.ZS",                  # Exports of goods and services (% of GDP)
    "manufacturing_value_added_pct_gdp": "NV.IND.MANF.ZS",  # Manufacturing, value added (% of GDP) -- output, not spend
}

INDICATOR_LABELS = {
    "total_expense_pct_gdp": "General Government Total Expense (% of GDP)",
    "defence_pct_gdp": "Defence/Military Expenditure (% of GDP)",
    "defence_pct_govt_exp": "Defence/Military Expenditure (% of Government Expenditure)",
    "health_pct_gdp": "Government Health Expenditure (% of GDP)",
    "exports_pct_gdp": "Exports of Goods and Services (% of GDP)",
    "manufacturing_value_added_pct_gdp": "Manufacturing Value Added (% of GDP) [output, not spend]",
}

# Categories the framework calls for that have no public API source and
# require a manual pull from Union Budget / Ministry documents.
MANUAL_SOURCE_CATEGORIES = {
    "space": {
        "label": "Space (ISRO / Department of Space) Budget",
        "reason": "No public API. Requires manual pull from Union Budget expenditure documents (Demand for Grants, Dept. of Space).",
        "suggested_source": "indiabudget.gov.in - Demand for Grants, Department of Space",
    },
    "manufacturing_incentives": {
        "label": "Manufacturing Incentive Spending (PLI schemes)",
        "reason": "No public API. Requires manual pull from Ministry of Commerce/Industry PLI disbursement reports.",
        "suggested_source": "Union Budget Demand for Grants, Dept. for Promotion of Industry and Internal Trade (DPIIT)",
    },
}


# ---------------------------------------------------------------------------
# Fetch helpers
# ---------------------------------------------------------------------------

def fetch_wb_indicator_series(country_code, indicator_code):
    """
    Fetch a single World Bank indicator series for one country.
    Returns a pandas Series indexed by year (int), sorted ascending.
    """
    url = f"{WB_BASE}/country/{country_code}/indicator/{indicator_code}"
    params = {
        "format": "json",
        "per_page": 1000,
        "date": f"{START_YEAR}:{END_YEAR}",
    }

    last_error = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            payload = resp.json()

            if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
                return pd.Series(dtype="float64")

            records = payload[1]
            years, values = [], []
            for rec in records:
                year = rec.get("date")
                if year is None:
                    continue
                years.append(int(year))
                values.append(rec.get("value"))

            series = pd.Series(data=values, index=years, dtype="float64").sort_index()
            return series

        except (requests.RequestException, ValueError, KeyError) as exc:
            last_error = exc
            if attempt < RETRY_ATTEMPTS:
                import time
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    print(f"  WARNING: failed to fetch {indicator_code} for {country_code}: {last_error}")
    return pd.Series(dtype="float64")


def fetch_gov_spending_data(country_code, indicators):
    """Fetch all indicators for one country, combined into a single year-indexed DataFrame."""
    series_list = []
    for key, code in indicators.items():
        s = fetch_wb_indicator_series(country_code, code)
        s.name = key
        series_list.append(s)
    df = pd.concat(series_list, axis=1).sort_index()
    return df


def fetch_peer_data(peer_codes, indicators):
    """Fetch the same indicators for each peer country. Returns {peer_code: DataFrame}."""
    peer_data = {}
    for peer in peer_codes:
        peer_data[peer] = fetch_gov_spending_data(peer, indicators)
    return peer_data


# ---------------------------------------------------------------------------
# Build JSON payloads
# ---------------------------------------------------------------------------

def build_trend_json(df, columns, label, extra_meta=None):
    """Build a year-indexed trend JSON for one or more indicator columns."""
    clean = df[columns].dropna(how="all")
    records = []
    for year, row in clean.iterrows():
        record = {"year": int(year)}
        for col in columns:
            record[col] = helper.clean_float(row[col], 2)
        records.append(record)

    meta_extra = {"label": label, "country": COUNTRY_CODE, "columns": columns}
    if extra_meta:
        meta_extra.update(extra_meta)

    return {
        "metadata": helper.metadata(extra=meta_extra),
        "data": records,
    }


def build_peer_comparison_json(india_df, peer_dfs, column, label):
    """Build a year-indexed comparison JSON of one indicator across India + peers."""
    combined = pd.DataFrame({COUNTRY_CODE: india_df[column]})
    for peer, df in peer_dfs.items():
        combined[peer] = df[column]
    combined = combined.dropna(how="all").sort_index()

    records = []
    for year, row in combined.iterrows():
        record = {"year": int(year)}
        for col in combined.columns:
            record[col] = helper.clean_float(row[col], 2)
        records.append(record)

    return {
        "metadata": helper.metadata(extra={
            "label": label,
            "indicator_column": column,
            "countries": list(combined.columns),
        }),
        "data": records,
    }


def build_spending_distribution_json(india_df):
    """Latest-year snapshot across spending categories, for a distribution/pie view."""
    clean = india_df.dropna(how="all")
    if clean.empty:
        latest_year, latest_row = None, {}
    else:
        latest_year = int(clean.index.max())
        latest_row = clean.loc[latest_year]

    categories = []
    for key, label in INDICATOR_LABELS.items():
        categories.append({
            "key": key,
            "label": label,
            "value": helper.clean_float(latest_row.get(key), 2) if len(latest_row) else None,
        })

    return {
        "metadata": helper.metadata(extra={
            "label": "Government Spending Distribution (Latest Year)",
            "latest_year": latest_year,
            "country": COUNTRY_CODE,
        }),
        "data": categories,
    }


def build_manual_source_flags_json():
    """Flags categories from the framework that require manual data entry."""
    entries = []
    for key, info in MANUAL_SOURCE_CATEGORIES.items():
        entries.append({
            "key": key,
            "label": info["label"],
            "status": "manual_source_required",
            "reason": info["reason"],
            "suggested_source": info["suggested_source"],
            "value": None,
        })

    return {
        "metadata": helper.metadata(extra={
            "label": "Government Spending Categories Requiring Manual Data Pull",
        }),
        "data": entries,
    }


def build_summary_json(india_df, distribution_json, manual_flags_json):
    """Consolidated latest-value snapshot across all indicators + manual flags."""
    clean = india_df.dropna(how="all")
    latest_year = int(clean.index.max()) if not clean.empty else None
    latest_row = clean.loc[latest_year] if latest_year is not None else {}

    api_sourced = {
        key: helper.clean_float(latest_row.get(key), 2) if len(latest_row) else None
        for key in INDICATORS
    }

    return {
        "metadata": helper.metadata(extra={
            "label": "Government Spending Summary",
            "latest_year": latest_year,
            "country": COUNTRY_CODE,
        }),
        "data": {
            "api_sourced_latest": api_sourced,
            "manual_source_required": [entry["key"] for entry in manual_flags_json["data"]],
        },
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    gov_spending_output_dir = os.path.join(OUTPUT_DIR, "government_spending")

    print("Fetching India government spending indicators (World Bank, annual)...")
    india_df = fetch_gov_spending_data(COUNTRY_CODE, INDICATORS)

    print("\nFetching peer government spending indicators (China, Vietnam, Indonesia, Bangladesh)...")
    peer_dfs = fetch_peer_data(PEER_CODES, INDICATORS)

    print("\nBuilding total_expense_trend.json...")
    helper.write_json(
        build_trend_json(india_df, ["total_expense_pct_gdp"], "General Government Total Expense"),
        "total_expense_trend.json", gov_spending_output_dir,
    )

    print("Building defence_spending_trend.json...")
    helper.write_json(
        build_trend_json(india_df, ["defence_pct_gdp", "defence_pct_govt_exp"], "Defence Spending"),
        "defence_spending_trend.json", gov_spending_output_dir,
    )

    print("Building healthcare_spending_trend.json...")
    helper.write_json(
        build_trend_json(india_df, ["health_pct_gdp"], "Government Health Expenditure"),
        "healthcare_spending_trend.json", gov_spending_output_dir,
    )

    print("Building exports_trend.json...")
    helper.write_json(
        build_trend_json(india_df, ["exports_pct_gdp"], "Exports of Goods and Services"),
        "exports_trend.json", gov_spending_output_dir,
    )

    print("Building defence_spending_peer_comparison.json...")
    helper.write_json(
        build_peer_comparison_json(india_df, peer_dfs, "defence_pct_gdp", "Defence Spending (% of GDP): India vs Peers"),
        "defence_spending_peer_comparison.json", gov_spending_output_dir,
    )

    print("Building exports_peer_comparison.json...")
    helper.write_json(
        build_peer_comparison_json(india_df, peer_dfs, "exports_pct_gdp", "Exports (% of GDP): India vs Peers"),
        "exports_peer_comparison.json", gov_spending_output_dir,
    )

    print("Building spending_distribution_latest.json...")
    distribution_json = build_spending_distribution_json(india_df)
    helper.write_json(distribution_json, "spending_distribution_latest.json", gov_spending_output_dir)

    print("Building manual_source_flags.json...")
    manual_flags_json = build_manual_source_flags_json()
    helper.write_json(manual_flags_json, "manual_source_flags.json", gov_spending_output_dir)

    print("Building government_spending_summary.json...")
    helper.write_json(
        build_summary_json(india_df, distribution_json, manual_flags_json),
        "government_spending_summary.json", gov_spending_output_dir,
    )

    print(f"\nDone. All JSON files written to ./{gov_spending_output_dir}/")


if __name__ == "__main__":
    main()