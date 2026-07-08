"""
INR Multi-Currency Analysis — JSON Output for React Frontend
================================================================

Analyzes the Indian Rupee against USD, GBP, EUR, JPY, CHF and writes
structured JSON files suitable for charting libraries like Recharts,
Chart.js, or D3 in a React app.
"""

import json
import os
from datetime import datetime, timezone
import yfinance as yf
import pandas as pd
import numpy as np

OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------

INR_PAIRS = {
    "USD_INR": "INR=X",
    "GBP_INR": "GBPINR=X",
    "EUR_INR": "EURINR=X",
    "JPY_INR": "JPYINR=X",
    "CHF_INR": "CHFINR=X",
}

CROSS_VS_USD = {
    "EUR_USD": "EURUSD=X",
    "GBP_USD": "GBPUSD=X",
    "USD_JPY": "USDJPY=X",
    "USD_CHF": "USDCHF=X",
}

EVENT_WINDOWS = {
    "2018_Rate_Hikes": ("2018-01-01", "2018-12-31"),
    "2020_COVID": ("2020-02-01", "2020-06-30"),
    "2022_Fed_Hiking": ("2022-01-01", "2022-12-31"),
}


# -----------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------

def metadata(source="yfinance", period="10y", extra=None):
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "period": period,
    }
    if extra:
        meta.update(extra)
    return meta


def write_json(obj, filename):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=str)
    print(f"  wrote {path}")


def clean_float(x, decimals=4):
    """Round and convert NaN -> None so it serializes as JSON null."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    return round(float(x), decimals)


# -----------------------------------------------------------------------
# 1. FETCH DATA
# -----------------------------------------------------------------------

def fetch_fx_data(tickers, period="10y", interval="1d"):
    data = {}
    for label, symbol in tickers.items():
        try:
            hist = yf.Ticker(symbol).history(period=period, interval=interval)
            if not hist.empty:
                data[label] = hist["Close"]
                print(f"  fetched {label} ({symbol}): {len(hist)} rows")
            else:
                print(f"  WARNING: no data for {label} ({symbol})")
        except Exception as e:
            print(f"  ERROR fetching {label} ({symbol}): {e}")
    df = pd.DataFrame(data)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df.dropna(how="all")


# -----------------------------------------------------------------------
# 2. REBASED PERFORMANCE -> wide-format JSON for a multi-line chart
# -----------------------------------------------------------------------

def build_rebased_json(df, base=100):
    clean = df.dropna()
    indexed = clean / clean.iloc[0] * base
    records = []
    for date, row in indexed.iterrows():
        record = {"date": date.strftime("%Y-%m-%d")}
        for col in indexed.columns:
            record[col] = clean_float(row[col], 2)
        records.append(record)
    return {
        "metadata": metadata(extra={"base_value": base, "pairs": list(df.columns)}),
        "data": records,
    }


# -----------------------------------------------------------------------
# 3. VOLATILITY SUMMARY -> array for a bar chart
# -----------------------------------------------------------------------

def build_volatility_json(df):
    daily_returns = df.pct_change().dropna()
    ann_vol = (daily_returns.std() * np.sqrt(252) * 100).sort_values(ascending=False)
    records = [
        {"pair": pair, "annualized_volatility_pct": clean_float(val, 2)}
        for pair, val in ann_vol.items()
    ]
    return {
        "metadata": metadata(extra={"calculation": "std(daily_returns) * sqrt(252) * 100"}),
        "data": records,
    }


# -----------------------------------------------------------------------
# 4. CROSS DECOMPOSITION -> is EUR/INR about INR or about EUR/USD?
# -----------------------------------------------------------------------

def build_decomposition_json(inr_df, usd_cross_df, pairs_to_compare):
    """
    pairs_to_compare: list of tuples like [("EUR_INR", "EUR_USD"), ("GBP_INR", "GBP_USD")]
    """
    results = []
    for inr_pair, usd_pair in pairs_to_compare:
        if inr_pair not in inr_df.columns or usd_pair not in usd_cross_df.columns:
            continue
        combined = pd.concat([inr_df[inr_pair], usd_cross_df[usd_pair]], axis=1).dropna()
        if len(combined) < 2:
            continue
        start_date, end_date = combined.index[0], combined.index[-1]
        pct_change = (combined.iloc[-1] / combined.iloc[0] - 1) * 100
        results.append({
            "inr_pair": inr_pair,
            "usd_cross_pair": usd_pair,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "inr_pair_pct_change": clean_float(pct_change[inr_pair], 2),
            "usd_cross_pct_change": clean_float(pct_change[usd_pair], 2),
        })
    return {
        "metadata": metadata(extra={
            "note": "Compares cumulative % change of an INR cross vs the equivalent USD cross "
                    "to separate rupee-driven moves from other-currency-driven moves."
        }),
        "data": results,
    }


# -----------------------------------------------------------------------
# 5. CORRELATION WITH EQUITY MARKET
# -----------------------------------------------------------------------

def build_correlation_json(fx_series, fx_label="USD_INR", equity_ticker="^NSEI",
                            equity_label="Nifty50", period="10y"):
    equity_hist = yf.Ticker(equity_ticker).history(period=period, interval="1d")["Close"]
    equity_hist.index = pd.to_datetime(equity_hist.index).tz_localize(None)
    combined = pd.concat([fx_series, equity_hist], axis=1).dropna()
    combined.columns = [fx_label, equity_label]
    returns = combined.pct_change().dropna()
    corr = returns[fx_label].corr(returns[equity_label])

    # also compute rolling correlation for a time-series chart
    window = 60
    rolling_corr = returns[fx_label].rolling(window).corr(returns[equity_label]).dropna()
    rolling_records = [
        {"date": date.strftime("%Y-%m-%d"), "rolling_correlation": clean_float(val, 3)}
        for date, val in rolling_corr.items()
    ]

    return {
        "metadata": metadata(extra={
            "fx_pair": fx_label,
            "equity_index": equity_label,
            "rolling_window_days": window,
        }),
        "overall_correlation": clean_float(corr, 3),
        "rolling_correlation": rolling_records,
    }


# -----------------------------------------------------------------------
# 6. EVENT WINDOW ANALYSIS -> array for a grouped bar chart
# -----------------------------------------------------------------------

def build_event_window_json(df, windows=EVENT_WINDOWS):
    results = []
    for event, (start, end) in windows.items():
        window = df.loc[start:end].dropna()
        if len(window) < 2:
            continue
        pct_change = (window.iloc[-1] / window.iloc[0] - 1) * 100
        for pair in df.columns:
            if pair in pct_change:
                results.append({
                    "event": event,
                    "start_date": start,
                    "end_date": end,
                    "pair": pair,
                    "pct_change": clean_float(pct_change[pair], 2),
                })
    return {
        "metadata": metadata(extra={"windows": {k: list(v) for k, v in windows.items()}}),
        "data": results,
    }


# -----------------------------------------------------------------------
# 7. RAW DATA -> full time series, in case frontend wants to compute its own views
# -----------------------------------------------------------------------

def build_raw_data_json(df):
    records = []
    for date, row in df.iterrows():
        record = {"date": date.strftime("%Y-%m-%d")}
        for col in df.columns:
            record[col] = clean_float(row[col], 4)
        records.append(record)
    return {
        "metadata": metadata(extra={"pairs": list(df.columns)}),
        "data": records,
    }


# -----------------------------------------------------------------------
# 8. MAIN
# -----------------------------------------------------------------------

if __name__ == "__main__":
    print("Fetching INR pairs (10y, daily)...")
    inr_df = fetch_fx_data(INR_PAIRS)

    print("\nFetching USD cross-rates (for decomposition)...")
    usd_cross_df = fetch_fx_data(CROSS_VS_USD)

    print("\nBuilding rebased_performance.json...")
    write_json(build_rebased_json(inr_df), "rebased_performance.json")

    print("\nBuilding volatility_summary.json...")
    write_json(build_volatility_json(inr_df), "volatility_summary.json")

    print("\nBuilding cross_decomposition.json...")
    pairs_to_compare = [
        ("EUR_INR", "EUR_USD"),
        ("GBP_INR", "GBP_USD"),
        ("JPY_INR", "USD_JPY"),
        ("CHF_INR", "USD_CHF"),
    ]
    write_json(build_decomposition_json(inr_df, usd_cross_df, pairs_to_compare),
               "cross_decomposition.json")

    print("\nBuilding correlation_summary.json...")
    write_json(build_correlation_json(inr_df["USD_INR"]), "correlation_summary.json")

    print("\nBuilding event_windows.json...")
    write_json(build_event_window_json(inr_df), "event_windows.json")

    print("\nBuilding raw_fx_data.json...")
    write_json(build_raw_data_json(inr_df), "raw_fx_data.json")

    print(f"\nDone. All JSON files written to ./{OUTPUT_DIR}/")
    