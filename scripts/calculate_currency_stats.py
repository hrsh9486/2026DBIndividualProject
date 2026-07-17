"""
INR Multi-Currency Analysis — JSON Output for React Frontend
================================================================

Analyzes the Indian Rupee against USD, GBP, EUR, JPY, CHF and writes
structured JSON files suitable for charting libraries like Recharts,
Chart.js, or D3 in a React app.
"""

import pandas as pd
import numpy as np
import os
import helper
from config import OUTPUT_DIR, INR_PAIRS, CROSS_VS_USD, EVENT_WINDOWS
from extractors.yfinance import fetch_close_prices
from validators import validate_correlation, validate_dated_rows


# -----------------------------------------------------------------------
# 1. FETCH DATA
# -----------------------------------------------------------------------

def fetch_fx_data(tickers, period="10y", interval="1d"):
    return fetch_close_prices(
        tickers,
        dataset="currency",
        period=period,
        interval=interval,
    ).dropna(how="all")


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
            record[col] = helper.clean_float(row[col], 2)
        records.append(record)
    validate_dated_rows(records, required_series=df.columns)
    return {
        "metadata": helper.metadata(extra={"base_value": base, "pairs": list(df.columns)}),
        "data": records,
    }


# -----------------------------------------------------------------------
# 3. VOLATILITY SUMMARY -> array for a bar chart
# -----------------------------------------------------------------------

def build_volatility_json(df):
    daily_returns = df.pct_change().dropna()
    ann_vol = (daily_returns.std() * np.sqrt(252) * 100).sort_values(ascending=False)
    records = [
        {"pair": pair, "annualized_volatility_pct": helper.clean_float(val, 2)}
        for pair, val in ann_vol.items()
    ]
    return {
        "metadata": helper.metadata(extra={"calculation": "std(daily_returns) * sqrt(252) * 100"}),
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
            "inr_pair_pct_change": helper.clean_float(pct_change[inr_pair], 2),
            "usd_cross_pct_change": helper.clean_float(pct_change[usd_pair], 2),
        })
    return {
        "metadata": helper.metadata(extra={
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
    equity_hist = fetch_close_prices(
        {equity_label: equity_ticker},
        dataset="currency_equity_correlation",
        period=period,
    )[equity_label]
    combined = pd.concat([fx_series, equity_hist], axis=1).dropna()
    combined.columns = [fx_label, equity_label]
    returns = combined.pct_change().dropna()
    corr = validate_correlation(helper.clean_float(returns[fx_label].corr(returns[equity_label]), 3))

    # also compute rolling correlation for a time-series chart
    window = 60
    rolling_corr = returns[fx_label].rolling(window).corr(returns[equity_label]).dropna()
    rolling_records = [
        {"date": date.strftime("%Y-%m-%d"), "rolling_correlation": helper.clean_float(val, 3)}
        for date, val in rolling_corr.items()
    ]

    return {
        "metadata": helper.metadata(extra={
            "fx_pair": fx_label,
            "equity_index": equity_label,
            "rolling_window_days": window,
        }),
        "overall_correlation": corr,
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
                    "pct_change": helper.clean_float(pct_change[pair], 2),
                })
    return {
        "metadata": helper.metadata(extra={"windows": {k: list(v) for k, v in windows.items()}}),
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
            record[col] = helper.clean_float(row[col], 4)
        records.append(record)
    validate_dated_rows(records, required_series=df.columns)
    return {
        "metadata": helper.metadata(extra={"pairs": list(df.columns)}),
        "data": records,
    }


# -----------------------------------------------------------------------
# 8. MAIN
# -----------------------------------------------------------------------

def main():
    currency_output_dir = os.path.join(OUTPUT_DIR, "currency")

    print("Fetching INR pairs (10y, daily)...")
    inr_df = fetch_fx_data(INR_PAIRS)

    print("\nFetching USD cross-rates (for decomposition)...")
    usd_cross_df = fetch_fx_data(CROSS_VS_USD)

    print("\nBuilding rebased_performance.json...")
    helper.write_json(build_rebased_json(inr_df), "rebased_performance.json", currency_output_dir)

    print("\nBuilding volatility_summary.json...")
    helper.write_json(build_volatility_json(inr_df), "volatility_summary.json", currency_output_dir)

    print("\nBuilding cross_decomposition.json...")
    pairs_to_compare = [
        ("EUR_INR", "EUR_USD"),
        ("GBP_INR", "GBP_USD"),
        ("JPY_INR", "USD_JPY"),
        ("CHF_INR", "USD_CHF"),
    ]
    helper.write_json(build_decomposition_json(inr_df, usd_cross_df, pairs_to_compare),
               "cross_decomposition.json", currency_output_dir)

    print("\nBuilding correlation_summary.json...")
    helper.write_json(build_correlation_json(inr_df["USD_INR"]), "correlation_summary.json", currency_output_dir)

    print("\nBuilding event_windows.json...")
    helper.write_json(build_event_window_json(inr_df), "event_windows.json", currency_output_dir)

    print("\nBuilding raw_fx_data.json...")
    helper.write_json(build_raw_data_json(inr_df), "raw_fx_data.json", currency_output_dir)

    print(f"\nDone. All JSON files written to ./{currency_output_dir}/")


if __name__ == "__main__":
    main()
