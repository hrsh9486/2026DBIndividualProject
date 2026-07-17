"""Build the validated market-performance artifact from Yahoo Finance."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf

from config import PROCESSED_DATA_DIR
from config.indicators import Contract
from exporters import publish_json
from transforms import build_market_bundle


LOGGER = logging.getLogger(__name__)
BASE_VALUE = 100
RISK_FREE_RATE = 0.0
INTERVAL = "1d"

MARKETS = {
    "NIFTY_50": {"label": "Nifty 50", "ticker": "^NSEI", "currency": "INR"},
    "SENSEX": {"label": "Sensex", "ticker": "^BSESN", "currency": "INR"},
    "NIFTY_BANK": {"label": "Nifty Bank", "ticker": "^NSEBANK", "currency": "INR"},
    "SP_500": {"label": "S&P 500", "ticker": "^GSPC", "currency": "USD"},
    "FTSE_100": {"label": "FTSE 100", "ticker": "^FTSE", "currency": "GBP"},
    "HANG_SENG": {"label": "Hang Seng", "ticker": "^HSI", "currency": "HKD"},
    "BOVESPA": {"label": "Bovespa", "ticker": "^BVSP", "currency": "BRL"},
    "EM_ETF": {"label": "iShares MSCI Emerging Markets ETF", "ticker": "EEM", "currency": "USD"},
}


def fetch_prices(period: str = "10y", interval: str = INTERVAL) -> pd.DataFrame:
    """Source-specific Yahoo extraction; calculations are performed elsewhere."""
    columns = {}
    for key, definition in MARKETS.items():
        history = yf.Ticker(definition["ticker"]).history(period=period, interval=interval)
        if history.empty:
            LOGGER.warning("No Yahoo data for %s (%s)", key, definition["ticker"])
            continue
        columns[key] = history["Close"]
        LOGGER.info("%s: extracted %d price rows", key, len(history))
    if not columns:
        raise RuntimeError("Yahoo Finance returned no market data")
    prices = pd.DataFrame(columns)
    prices.index = pd.to_datetime(prices.index, utc=True).tz_localize(None)
    return prices.groupby(prices.index.date).last().sort_index()


def build_payload(prices: pd.DataFrame, *, interval: str = INTERVAL) -> dict:
    markets, correlations = build_market_bundle(
        prices,
        {key: value for key, value in MARKETS.items() if key in prices.columns},
        base_value=BASE_VALUE,
        risk_free_rate=RISK_FREE_RATE,
    )
    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "Yahoo Finance via yfinance",
            "start_date": pd.Timestamp(prices.index.min()).strftime("%Y-%m-%d"),
            "end_date": pd.Timestamp(prices.index.max()).strftime("%Y-%m-%d"),
            "base_value": BASE_VALUE,
            "risk_free_rate": RISK_FREE_RATE,
            "interval": interval,
        },
        "markets": markets,
        "correlations": correlations,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    prices = fetch_prices()
    payload = build_payload(prices)
    output_path = PROCESSED_DATA_DIR / "equity" / "market_performance.json"
    publish_json(payload, output_path, Contract.MARKET_PERFORMANCE.value)
    LOGGER.info("Published %d markets to %s", len(payload["markets"]), output_path)


if __name__ == "__main__":
    main()
