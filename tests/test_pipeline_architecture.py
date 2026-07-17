"""Contract and quality-gate tests for the restructured pipeline."""

from datetime import date
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from builders import build_annual_country_payload  # noqa: E402
from config.indicators import Contract, get_indicator  # noqa: E402
from models import CanonicalRecord  # noqa: E402
from validators import DataQualityError, validate_payload, validate_records  # noqa: E402

try:
    import pandas as pd
    from build_yfinance_markets import build_payload
except ModuleNotFoundError:
    pd = None
    build_payload = None


class RegistryAndAnnualContractTests(unittest.TestCase):
    def test_registry_builds_schema_valid_full_coverage_payload(self):
        spec = get_indicator("labour_force_participation")
        records = [
            CanonicalRecord(
                date=date(2024, 12, 31),
                entity="IND",
                indicator=spec.key,
                value=55.2,
                unit=spec.unit,
                frequency=spec.frequency,
                source="World Bank Indicators API",
            ),
            CanonicalRecord(
                date=date(2025, 12, 31),
                entity="CHN",
                indicator=spec.key,
                value=66.1,
                unit=spec.unit,
                frequency=spec.frequency,
                source="World Bank Indicators API",
            ),
        ]
        payload = build_annual_country_payload(
            spec,
            validate_records(records, expected_frequency="annual"),
            country="IND",
            peers=["CHN"],
            start_year=2024,
            end_year=2025,
        )
        self.assertEqual(payload["india"], [
            {"year": 2024, "value": 55.2},
            {"year": 2025, "value": None},
        ])
        validate_payload(payload, Contract.ANNUAL_COUNTRY_SERIES.value)

    def test_duplicate_records_fail_quality_gate(self):
        record = CanonicalRecord(
            date=date(2025, 12, 31),
            entity="IND",
            indicator="example",
            value=1.0,
            unit="index",
            frequency="annual",
            source="test",
        )
        with self.assertRaises(DataQualityError):
            validate_records([record, record])


class MarketContractTests(unittest.TestCase):
    @unittest.skipIf(pd is None, "pandas/yfinance runtime dependencies are not installed")
    def test_market_builder_emits_delivered_contract(self):
        prices = pd.DataFrame(
            {"NIFTY_50": [100.0, 101.0, 99.0, 103.0]},
            index=pd.date_range("2025-01-01", periods=4, freq="D"),
        )
        payload = build_payload(prices)
        self.assertEqual(payload["markets"]["NIFTY_50"]["series"][0]["normalized_value"], 100.0)
        validate_payload(payload, Contract.MARKET_PERFORMANCE.value)


if __name__ == "__main__":
    unittest.main()
