"""Runtime configuration shared by source-specific pipeline jobs."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SCHEMA_DIR = PROJECT_ROOT / "schemas"

# Backwards-compatible name used by the existing scripts.
OUTPUT_DIR = str(DATA_DIR)
TRADING_DAYS = 252

WB_BASE = "https://api.worldbank.org/v2"
REQUEST_TIMEOUT = 20
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2
START_YEAR = 1991
COUNTRY_CODE = "IND"
PEER_CODES = ["CHN", "VNM", "IDN", "BGD"]
ALL_COUNTRIES = [COUNTRY_CODE, *PEER_CODES]

INDIAN_MARKETS = {
    "Nifty 50": "^NSEI",
    "Sensex": "^BSESN",
    "Nifty Bank": "^NSEBANK",
}

GLOBAL_MARKETS = {
    "S&P500": "^GSPC",
    "FTSE100": "^FTSE",
    "HangSeng_China": "^HSI",
    "Bovespa_Brazil": "^BVSP",
    "EM_ETF": "EEM",
}

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
