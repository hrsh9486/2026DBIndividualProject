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



# -----------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------

OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)
TRADING_DAYS = 252

ETFS = {
    # Indian ETS
    "Nifty 50": "^NSEI",
    "Sensex": "^BSESN",
    "Nifty Bank": "^NSEBANK",

    # Global ETFS
    "S&P500": "^GSPC",
    "FTSE100": "^FTSE",
    "HangSeng_China": "^HSI",
    "Bovespa_Brazil": "^BVSP",
    "EM_ETF": "EEM",      
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


# -----------------------------------------------------------------------
# 2. CALCULATE RAW STATISTICS
# -----------------------------------------------------------------------

def total_return(price: pd.Series) -> float:
    return float(price.iloc[-1] / price.iloc[0] - 1)


def cagr(price: pd.Series) -> float:
    years = len(price) / TRADING_DAYS
    return float((price.iloc[-1] / price.iloc[0]) ** (1 / years) - 1)


def annual_return(ret: pd.Series) -> float:
    return float(ret.mean() * TRADING_DAYS)


def annual_volatility(ret: pd.Series) -> float:
    return float(ret.std() * np.sqrt(TRADING_DAYS))


def sharpe_ratio(
    ret: pd.Series,
    risk_free_rate: float = 0.0,
) -> float:
    excess = ret - risk_free_rate / TRADING_DAYS
    return float(
        excess.mean()
        / ret.std()
        * np.sqrt(TRADING_DAYS)
    )


def downside_volatility(ret: pd.Series) -> float:
    downside = ret[ret < 0]
    if len(downside) == 0:
        return 0.0
    return float(
        downside.std() * np.sqrt(TRADING_DAYS)
    )


def sortino_ratio(
    ret: pd.Series,
    risk_free_rate: float = 0.0,
) -> float:
    downside = downside_volatility(ret)
    if downside == 0:
        return 0.0
    return float(
        (annual_return(ret) - risk_free_rate)
        / downside
    )


def max_drawdown(price: pd.Series) -> float:
    running_max = price.cummax()
    drawdown = price / running_max - 1
    return float(drawdown.min())


def calmar_ratio(
    price: pd.Series,
    ret: pd.Series,
) -> float:
    dd = abs(max_drawdown(price))
    if dd == 0:
        return 0.0
    return float(cagr(price) / dd)



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
            "total_return": total_return(prices[market]),
            "cagr": cagr(prices[market]),
            "annual_return": annual_return(
                returns[market]
            ),
            "annual_volatility": annual_volatility(
                returns[market]
            ),
            "sharpe_ratio": sharpe_ratio(
                returns[market]
            ),
            "sortino_ratio": sortino_ratio(
                returns[market]
            ),
            "max_drawdown": max_drawdown(
                prices[market]
            ),
            "calmar_ratio": calmar_ratio(
                prices[market],
                returns[market],
            ),
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

# ==========================================================
# 5. MODEL GROWTH OF £100
# ==========================================================

def growth_of_100(
    prices: pd.DataFrame,
) -> dict:
    growth = prices.divide(
        prices.iloc[0]
    ).multiply(100)
    return {
        "dates": growth.index.astype(str).tolist(),
        "series": {
            col: growth[col].round(2).tolist()
            for col in growth.columns
        },
    }


# ==========================================================
# 6. CALCULATE ROLLING STATISTICS
# ==========================================================

def rolling_returns(
    returns: pd.DataFrame,
    window: int = 252,
):
    rolling = (
        (1 + returns)
        .rolling(window)
        .apply(np.prod)
        - 1
    )
    return {
        "dates": rolling.index.astype(str).tolist(),
        "series": {
            col: rolling[col]
            .round(4)
            .fillna(None)
            .tolist()
            for col in rolling.columns
        },
    }


def rolling_volatility(
    returns,
    window=252,
):
    rolling = (
        returns
        .rolling(window)
        .std()
        * np.sqrt(TRADING_DAYS)
    )
    return {
        "dates": rolling.index.astype(str).tolist(),
        "series": {
            c: rolling[c]
            .round(4)
            .fillna(None)
            .tolist()
            for c in rolling.columns
        },
    }


def rolling_sharpe(
    returns,
    window=252,
):
    mean = (
        returns
        .rolling(window)
        .mean()
        * TRADING_DAYS
    )
    std = (
        returns
        .rolling(window)
        .std()
        * np.sqrt(TRADING_DAYS)
    )
    sharpe = mean / std
    return {
        "dates": sharpe.index.astype(str).tolist(),
        "series": {
            c: sharpe[c]
            .round(4)
            .fillna(None)
            .tolist()
            for c in sharpe.columns
        },
    }


# -----------------------------------------------------------------------
# 8. CREATE JSON OBJECT
# -----------------------------------------------------------------------

def build_json(prices_df, returns_df, summary, rankings):
    return {
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

        "rankings": rankings,
    }


# -----------------------------------------------------------------------
# 8. MAIN
# -----------------------------------------------------------------------

if __name__ == "__main__":
    print("Fetching ETF History (10y, daily)...")
    prices_df = fetch_etf_data(ETFS)
    # Normalise against different time zones
    # Calculate daily returns
    prices_df = prices_df.dropna()
    returns_df = prices_df.pct_change().dropna()

    summary = build_summary(prices_df, returns_df)
    rankings = build_rankings(summary) 
    
    print("\nBuilding etf_analysis.json")
    etf_analysis_obj = build_json(prices_df, returns_df, summary, rankings)
    write_json(etf_analysis_obj, "etf_analysis.json")
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