"""
demographics_human_capital.py

Bucket 04: Demographics & Human Capital
Pulls India (and comparator) demographic + human capital indicators from the
World Bank API (no key required) and writes structured JSON outputs for the
frontend dashboard, matching the pattern used by inr_currency_analysis.py.

Outputs (written to OUTPUT_DIR):
  - urban_population.json          Urban population % of total, time series
  - literacy_rate.json              Adult literacy rate, time series
  - electricity_access.json         Access to electricity % of population
  - labor_force_participation.json  Labor force participation rate (15+)
  - dependency_ratio.json           Age dependency ratio + working-age share
  - demographics_summary.json       Latest-value snapshot across all indicators
                                     with peer comparison (China, Vietnam, Indonesia, Bangladesh)

"""

import math
import os
import time
from datetime import datetime, timezone
import pandas as pd

import requests
import helper
from config import OUTPUT_DIR, WB_BASE, REQUEST_TIMEOUT, RETRY_ATTEMPTS, RETRY_BACKOFF_SECONDS, START_YEAR, COUNTRY_CODE, PEER_CODES

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

END_YEAR = pd.Timestamp.now().year
OUTPUT_DIR = os.path.join(OUTPUT_DIR, "demographics")

# World Bank indicator codes for this bucket
INDICATORS = {
    "urban_population_pct": "SP.URB.TOTL.IN.ZS",       # Urban population (% of total)
    "adult_literacy_rate": "SE.ADT.LITR.ZS",            # Adult literacy rate (% ages 15+)
    "labor_force_participation": "SL.TLF.CACT.ZS",      # Labor force participation rate (% ages 15+)
    "age_dependency_ratio": "SP.POP.DPND",              # Age dependency ratio (% of working-age pop)
    "working_age_share_pct": "SP.POP.1564.TO.ZS",       # Population ages 15-64 (% of total)
    "youth_unemployment_rate": "SL.UEM.1524.ZS",
    "female_to_male_lfpr_ration": "SL.TLF.CACT.FM.NE.ZS",
    "school_enrollment_gross_secondary": "SE.SEC.ENRR",
    "school_enrollment_gross_tertiary": "SE.TER.ENRR",
    "pct_gdb_secondary_expenditure": "SE.XPD.SECO.PC.ZS",
}



SINGLE_SERIES_SPECS = [
    ("urban_population_pct", INDICATORS["urban_population_pct"], "urban_population.json", "Urban Population (% of total)"),
    ("adult_literacy_rate", INDICATORS["adult_literacy_rate"], "literacy_rate.json", "Adult Literacy Rate (% ages 15+)"),
    ("labor_force_participation", INDICATORS["labor_force_participation"], "labor_force_participation.json", "Labor Force Participation Rate (% ages 15+)"),
    ("working_age_share_pct", INDICATORS["working_age_share_pct"], "working_age_share_pct.json", "Working Age Population Share  (% ages 15-64)"),
    ("youth_unemployment_rate", INDICATORS["youth_unemployment_rate"], "youth_unemployment_rate.json", "Youth Unemployment Rate (% ages 15-24)"),
    ("female_to_male_lfpr_ration", INDICATORS["female_to_male_lfpr_ration"], "female_to_male_lfpr_ration.json", "Female to Male LFPR Ratio (% ages 15+)"),
    ("school_enrollment_gross_secondary", INDICATORS["school_enrollment_gross_secondary"], "school_enrollment_gross_secondary.json", "Secondary Education Enrollment (% of total)"),
    ("school_enrollment_gross_tertiary", INDICATORS["school_enrollment_gross_tertiary"], "school_enrollment_gross_tertiary.json", "Tertiary Education Enrollment (% of total)"),
    ("pct_gdb_secondary_expenditure", INDICATORS["pct_gdb_secondary_expenditure"], "pct_gdb_secondary_expenditure.json", "Government expenditure on Secondary Education (% of GDP)"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_float(value):
    """Convert a value to a JSON-safe float, mapping NaN/None/inf to null."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def fetch_indicator(country_code, indicator_code):
    """
    Fetch a single World Bank indicator series for one country.
    Returns a list of {year, value} dicts sorted ascending by year.
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
                return []

            records = payload[1]
            series = []
            for rec in records:
                year = rec.get("date")
                val = clean_float(rec.get("value"))
                if year is None:
                    continue
                series.append({"year": int(year), "value": val})

            series.sort(key=lambda r: r["year"])
            return series

        except (requests.RequestException, ValueError, KeyError) as exc:
            last_error = exc
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    print(f"  WARNING: failed to fetch {indicator_code} for {country_code}: {last_error}")
    return []


def latest_non_null(series):
    """Return the most recent {year, value} entry where value is not None."""
    for rec in reversed(series):
        if rec["value"] is not None:
            return rec
    return None


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def build_metadata():
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "World Bank Open Data API",
        "country": COUNTRY_CODE,
        "peers": PEER_CODES,
        "start_year": START_YEAR,
        "end_year": END_YEAR,
    }


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

def build_single_series_output(indicator_code, filename, label):
    """For indicators reported primarily as India's own time series (with peers for context)."""
    print(f"Fetching {label} ({indicator_code}) ...")

    india_series = fetch_indicator(COUNTRY_CODE, indicator_code)

    peer_series = {}
    for peer in PEER_CODES:
        peer_series[peer] = fetch_indicator(peer, indicator_code)

    output = {
        "metadata": {**build_metadata(), "indicator_code": indicator_code, "label": label},
        "india": india_series,
        "peers": peer_series,
        "latest": {
            "india": latest_non_null(india_series),
            "peers": {p: latest_non_null(s) for p, s in peer_series.items()},
        },
    }

    helper.write_json(output, filename, OUTPUT_DIR)
    return output


def build_dependency_ratio_output():
    """Combines age dependency ratio with working-age population share."""
    print("Fetching age dependency ratio + working-age population share ...")

    dep_series = fetch_indicator(COUNTRY_CODE, INDICATORS["age_dependency_ratio"])
    working_age_series = fetch_indicator(COUNTRY_CODE, INDICATORS["working_age_share_pct"])

    # merge by year for convenience on the frontend
    by_year = {}
    for rec in dep_series:
        by_year.setdefault(rec["year"], {})["age_dependency_ratio"] = rec["value"]
    for rec in working_age_series:
        by_year.setdefault(rec["year"], {})["working_age_share_pct"] = rec["value"]

    merged = [
        {"year": year, **vals}
        for year, vals in sorted(by_year.items())
    ]

    output = {
        "metadata": {
            **build_metadata(),
            "indicator_codes": {
                "age_dependency_ratio": INDICATORS["age_dependency_ratio"],
                "working_age_share_pct": INDICATORS["working_age_share_pct"],
            },
            "label": "Age Dependency Ratio & Working-Age Population Share",
            "note": "Lower dependency ratio + rising working-age share = 'demographic dividend' window",
        },
        "series": merged,
        "latest": merged[-1] if merged else None,
    }

    helper.write_json(output, "dependency_ratio.json", OUTPUT_DIR)
    return output


def build_summary(all_outputs):
    """Latest-value snapshot across every indicator, India vs peers."""
    print("Building demographics summary ...")

    summary = {
        "metadata": build_metadata(),
        "indicators": {},
    }

    for key, output in all_outputs.items():
        if key == "dependency_ratio":
            continue
        latest = output.get("latest", {})
        summary["indicators"][key] = {
            "label": output["metadata"]["label"],
            "india_latest": latest.get("india"),
            "peers_latest": latest.get("peers"),
        }

    # dependency ratio has a different shape, add separately
    dep_output = all_outputs.get("dependency_ratio")
    if dep_output:
        summary["indicators"]["dependency_ratio"] = {
            "label": dep_output["metadata"]["label"],
            "india_latest": dep_output.get("latest"),
        }

    helper.write_json(summary, "demographics_summary.json", OUTPUT_DIR)
    return summary


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ensure_output_dir()

    outputs = {}

    # I've commented these out because fetching is really slow for some reason - uncomment if you need to rebuild specific jsons
    for key, indicator_code, filename, label in SINGLE_SERIES_SPECS:
        outputs[key] = build_single_series_output(indicator_code, filename, label)
    outputs["dependency_ratio"] = build_dependency_ratio_output()

    build_summary(outputs)

    print("=" * 70)
    print("Done. Outputs written to:", os.path.abspath(OUTPUT_DIR))
    print("=" * 70)


if __name__ == "__main__":
    main()