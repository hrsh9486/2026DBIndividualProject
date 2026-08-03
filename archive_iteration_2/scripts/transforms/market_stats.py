"""Market calculations used by the market-performance contract."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from config import TRADING_DAYS
from helper import clean_float


def _summary(prices: pd.Series, returns: pd.Series, risk_free_rate: float) -> dict:
    years = max(len(prices) / TRADING_DAYS, 1 / TRADING_DAYS)
    total_return = prices.iloc[-1] / prices.iloc[0] - 1
    cagr = (prices.iloc[-1] / prices.iloc[0]) ** (1 / years) - 1
    volatility = returns.std() * math.sqrt(TRADING_DAYS)
    excess = returns - risk_free_rate / TRADING_DAYS
    sharpe = excess.mean() / returns.std() * math.sqrt(TRADING_DAYS) if returns.std() else None
    drawdown = prices / prices.cummax() - 1
    return {
        "total_return": clean_float(total_return),
        "cagr": clean_float(cagr),
        "annualized_volatility": clean_float(volatility),
        "sharpe_ratio": clean_float(sharpe),
        "max_drawdown": clean_float(drawdown.min()),
    }


def build_market_bundle(
    prices: pd.DataFrame,
    market_definitions: dict[str, dict[str, str]],
    *,
    base_value: float = 100,
    risk_free_rate: float = 0.0,
    rolling_window: int = 252,
) -> tuple[dict, list[dict]]:
    """Return schema-ready market objects and pairwise correlations."""
    if prices.empty:
        raise ValueError("Cannot build market performance from empty prices")
    prices = prices.sort_index()
    returns = prices.pct_change(fill_method=None)
    markets = {}
    for key, definition in market_definitions.items():
        series_prices = prices[key].dropna()
        if series_prices.empty:
            continue
        series_returns = series_prices.pct_change(fill_method=None)
        normalized = series_prices / series_prices.iloc[0] * base_value
        drawdown = series_prices / series_prices.cummax() - 1
        rolling_volatility = series_returns.rolling(rolling_window).std() * np.sqrt(TRADING_DAYS)
        observations = []
        for observation_date, price in series_prices.items():
            observations.append(
                {
                    "date": pd.Timestamp(observation_date).strftime("%Y-%m-%d"),
                    "price": clean_float(price),
                    "normalized_value": clean_float(normalized.loc[observation_date]),
                    "return": clean_float(series_returns.get(observation_date)),
                    "drawdown": clean_float(drawdown.loc[observation_date]),
                    "rolling_volatility": clean_float(rolling_volatility.get(observation_date)),
                }
            )
        markets[key] = {
            "label": definition["label"],
            "ticker": definition["ticker"],
            "currency": definition["currency"],
            "summary": _summary(series_prices, series_returns.dropna(), risk_free_rate),
            "series": observations,
        }

    correlations = []
    correlation_matrix = returns.corr()
    keys = list(markets)
    for position, market_a in enumerate(keys):
        for market_b in keys[position + 1:]:
            correlations.append(
                {
                    "market_a": market_a,
                    "market_b": market_b,
                    "correlation": clean_float(correlation_matrix.loc[market_a, market_b]),
                    "window": None,
                }
            )
    return markets, correlations
