"""Yahoo Finance price extraction with immutable raw landing."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

from config import RAW_DATA_DIR
from exporters import write_json_atomic


def fetch_close_prices(
    tickers: dict[str, str],
    *,
    dataset: str,
    period: str = "10y",
    interval: str = "1d",
    raw_root: str | Path = RAW_DATA_DIR / "yfinance",
) -> pd.DataFrame:
    """Fetch close prices and preserve each successful raw series."""
    columns = {}
    for key, ticker in tickers.items():
        history = yf.Ticker(ticker).history(period=period, interval=interval)
        if history.empty:
            continue
        series = history["Close"]
        columns[key] = series
        _land_series(series, key, ticker, dataset, period, interval, Path(raw_root))

    if not columns:
        raise RuntimeError(f"Yahoo Finance returned no data for {dataset}")
    frame = pd.DataFrame(columns)
    frame.index = pd.to_datetime(frame.index, utc=True).tz_localize(None)
    return frame.groupby(frame.index.date).last().sort_index()


def _land_series(
    series: pd.Series,
    key: str,
    ticker: str,
    dataset: str,
    period: str,
    interval: str,
    raw_root: Path,
) -> Path:
    retrieved = datetime.now(timezone.utc)
    observations = [
        {"date": pd.Timestamp(index).strftime("%Y-%m-%d"), "close": float(value)}
        for index, value in series.dropna().items()
    ]
    payload = {
        "retrieved_at": retrieved.isoformat(),
        "source_url": f"https://finance.yahoo.com/quote/{ticker}/history",
        "ticker": ticker,
        "period": period,
        "interval": interval,
        "observations": observations,
    }
    checksum = hashlib.sha256(
        json.dumps(payload["observations"], sort_keys=True).encode("utf-8")
    ).hexdigest()
    path = raw_root / retrieved.date().isoformat() / dataset / f"{key}-{checksum[:12]}.json"
    if not path.exists():
        payload["sha256"] = checksum
        write_json_atomic(payload, path)
    return path
