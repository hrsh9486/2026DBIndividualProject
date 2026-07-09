"""
INR Multi-Currency Analysis — JSON Output for React Frontend
================================================================

Analyzes the Indian Rupee against USD, GBP, EUR, JPY, CHF and writes
structured JSON files suitable for charting libraries like Recharts,
Chart.js, or D3 in a React app.
"""

import yfinance as yf
import pandas as pd
import helper
from config import INDIAN_MARKETS, GLOBAL_MARKETS, OUTPUT_DIR
import correlations
import base_stats




# -----------------------------------------------------------------------
# FETCH DATA
# -----------------------------------------------------------------------

def fetch_etf_data(tickers, period="10y", interval="1d"):
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
    # df.index = pd.to_datetime(df.index).tz_localize(None)

    df.index = pd.to_datetime(df.index)
    df = df.groupby(df.index.date).max()
    df.index.name = 'Date'
    return df.dropna(how="all")


# ==========================================================
# 3. BUILD SUMMARY OF STATISTICS
# ==========================================================

def build_summary(
    prices: pd.DataFrame,
    returns: pd.DataFrame,
) -> dict:

    summary = {}
    for market in prices.columns:
        summary[market] = {
            "total_return": base_stats.total_return(prices[market]),
            "cagr": base_stats.cagr(prices[market]),
            "annual_return": base_stats.annual_return(returns[market]),
            "annual_volatility": base_stats.annual_volatility(returns[market]),
            "sharpe_ratio": base_stats.sharpe_ratio(returns[market]),
            "sortino_ratio": base_stats.sortino_ratio(returns[market]),
            "max_drawdown": base_stats.max_drawdown(prices[market]),
            "calmar_ratio": base_stats.calmar_ratio(prices[market],returns[market],),
        }

    return summary


# ==========================================================
# 4. RANK ETFS BASED ON SUMMARY
# ==========================================================

def build_rankings(summary: dict):
    rankings = {}
    metrics = list(
        next(iter(summary.values())).keys()
    )
    for metric in metrics:
        reverse = metric != "max_drawdown"
        rankings[metric] = sorted(
            summary.keys(),
            key=lambda x: summary[x][metric],
            reverse=reverse,
        )
    return rankings

# -----------------------------------------------------------------------
# 8. CREATE JSON OBJECT
# -----------------------------------------------------------------------

def build_summary_json(prices_df, returns_df):
    summary = build_summary(prices_df, returns_df)
    return {
        "metadata": {
            "markets": list(prices_df.columns),
            "start_date": str(prices_df.index[0]),
            "end_date": str(prices_df.index[-1]),
            "trading_days": len(prices_df),
        },

        "summary": summary,
        "rankings": build_rankings(summary),
        "growth": base_stats.growth_of_100(prices_df),
        "rolling_returns": base_stats.rolling_returns(returns_df),
        "rolling_volatility": base_stats.rolling_volatility(returns_df),
        "rolling_sharpe": base_stats.rolling_sharpe(returns_df),
    }



def build_correlations_json(returns_df):
    pearson = correlations.pearson_correlation(returns_df, INDIAN_MARKETS, GLOBAL_MARKETS)
    rolling = correlations.rolling_pearson(returns_df, INDIAN_MARKETS, GLOBAL_MARKETS,)
    stability = correlations.correlation_stability(rolling)
    strongest = correlations.strongest_global_market(pearson)
    rankings = correlations.ranked_global_markets(pearson) 



    return {
        "metadata": {
            "markets": list(returns_df.columns),
            "start_date": str(returns_df.index[0]),
            "end_date": str(returns_df.index[-1]),
            "trading_days": len(returns_df),
        },

        "pearson": pearson,
        "stability": stability,
        "strongest": strongest,
        "rankings": rankings,
        "rolling": rolling,
    
    }





# -----------------------------------------------------------------------
# 8. MAIN
# -----------------------------------------------------------------------

if __name__ == "__main__":
    print("Fetching ETF History (10y, daily)...")
    ETFS = INDIAN_MARKETS | GLOBAL_MARKETS
    prices_df = fetch_etf_data(ETFS).dropna()
    returns_df = prices_df.pct_change().dropna()
    print("\nBuilding etf_analysis.json")
    etf_base_obj = build_summary_json(prices_df, returns_df)
    # etf_correlation_obj = build_correlations_json(returns_df)
    helper.write_json(etf_base_obj, "etf_base_stats.json", f"{OUTPUT_DIR}/etf")
    # helper.write_json(etf_correlation_obj, "etf_correlation_stats.json", f"{OUTPUT_DIR}/etf")
    print(f"\nDone. All JSON files written to ./{OUTPUT_DIR}/")
    



# INTENDED OUTPUT FORMAT
# =========================================================
'''
"metadata": {

    "markets": list(
        prices_df.columns
    ),

    "start_date": str(
        prices_df.index[0]
    ),

    "end_date": str(
        prices_df.index[-1]
    ),

    "trading_days": len(
        prices_df
    ),
},

"summary": summary,

"rankings": build_rankings(
    summary
),

"timeseries": {

    "growth": growth_of_100(
        prices
    ),

    "rolling_returns":
        rolling_returns(
            returns
        ),

    "rolling_volatility":
        rolling_volatility(
            returns
        ),

    "rolling_sharpe":
        rolling_sharpe(
            returns
        ),
},
}


'''