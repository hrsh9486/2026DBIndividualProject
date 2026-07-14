"""
calculate_etf_stats.py

Shared ETF return and risk statistics used by the ETF analysis bucket.
The functions return plain pandas objects or JSON-ready dictionaries,
but do not write files themselves.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import TRADING_DAYS

# -----------------------------------------------------------------------
# METHODS TO CALCULATE RAW FINANCIAL STATISTICS
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
# MODEL GROWTH OF £100 IN DIFFERENT MARKETS
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
# CALCULATE ROLLING STATISTICS
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
