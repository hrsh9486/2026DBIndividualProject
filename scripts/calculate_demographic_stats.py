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

Run:
    python demographics_human_capital.py
"""

import json
import math
import os
import time
from datetime import datetime, timezone

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

WB_BASE = "https://api.worldbank.org/v2"

COUNTRY_CODE = "IND"
PEER_CODES = ["CHN", "VNM", "IDN", "BGD"]  # China+1 comparators
ALL_COUNTRIES = [COUNTRY_CODE] + PEER_CODES

START_YEAR = 1991
END_YEAR = datetime.now().year

OUTPUT_DIR = os.path.join("data", "demographics")

# World Bank indicator codes for this bucket
INDICATORS = {
    "urban_population_pct": "SP.URB.TOTL.IN.ZS",       # Urban population (% of total)
    "adult_literacy_rate": "SE.ADT.LITR.ZS",            # Adult literacy rate (% ages 15+)
    "electricity_access_pct": "EG.ELC.ACCS.ZS",         # Access to electricity (% of population)
    "labor_force_participation": "SL.TLF.CACT.ZS",      # Labor force participation rate (% ages 15+)
    "age_dependency_ratio": "SP.POP.DPND",              # Age dependency ratio (% of working-age pop)
    "working_age_share_pct": "SP.POP.1564.TO.ZS",       # Population ages 15-64 (% of total)
}

REQUEST_TIMEOUT = 20
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2


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


def write_json(filename, payload):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"  wrote {path}")


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

def build_single_series_output(indicator_key, indicator_code, filename, label):
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

    write_json(filename, output)
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

    write_json("dependency_ratio.json", output)
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

    write_json("demographics_summary.json", summary)
    return summary


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ensure_output_dir()

    outputs = {}

    # I've commented these out because fetching is really slow for some reason - uncomment if you need to rebuild specific jsons
    outputs["urban_population_pct"] = build_single_series_output(
        "urban_population_pct", INDICATORS["urban_population_pct"],
        "urban_population.json", "Urban Population (% of total)",
    )
    outputs["adult_literacy_rate"] = build_single_series_output(
        "adult_literacy_rate", INDICATORS["adult_literacy_rate"],
        "literacy_rate.json", "Adult Literacy Rate (% ages 15+)",
    )
    outputs["electricity_access_pct"] = build_single_series_output(
        "electricity_access_pct", INDICATORS["electricity_access_pct"],
        "electricity_access.json", "Access to Electricity (% of population)",
    )
    outputs["labor_force_participation"] = build_single_series_output(
        "labor_force_participation", INDICATORS["labor_force_participation"],
        "labor_force_participation.json", "Labor Force Participation Rate (% ages 15+)",
    )
    outputs["dependency_ratio"] = build_dependency_ratio_output()

    build_summary(outputs)

    print("=" * 70)
    print("Done. Outputs written to:", os.path.abspath(OUTPUT_DIR))
    print("=" * 70)


if __name__ == "__main__":
    main()