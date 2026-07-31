from datetime import datetime
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from config.capex_analysis import CAPEX_MARKETS  # noqa: E402
from transforms.capex_analysis import (  # noqa: E402
    build_lag_analysis,
    build_sector_performance_payload,
    classify_summary,
)
from extractors.corporate_fundamentals import CorporateFundamental  # noqa: E402
from transforms.corporate_fundamentals import build_corporate_fundamentals_payload  # noqa: E402
from validators import validate_payload  # noqa: E402


class CapexMarketTests(unittest.TestCase):
    def setUp(self):
        dates = pd.date_range("2018-04-01", periods=84, freq="ME")
        self.prices = pd.DataFrame({
            "CAPITAL_GOODS": [100 * (1.018 ** index) for index in range(len(dates))],
            "INFRASTRUCTURE": [100 * (1.014 ** index) for index in range(len(dates))],
            "MANUFACTURING": [100 * (1.012 ** index) for index in range(len(dates))],
            "NIFTY_50": [100 * (1.008 ** index) for index in range(len(dates))],
            "FMCG": [100 * (1.006 ** index) for index in range(len(dates))],
        }, index=dates)
        self.definitions = {
            market.key: {"label": market.label, "ticker": market.ticker, "role": market.role}
            for market in CAPEX_MARKETS
        }

    def test_relative_wealth_uses_nifty_benchmark(self):
        payload = build_sector_performance_payload(self.prices, self.definitions)
        validate_payload(payload, "market_performance.schema.json")
        capital = payload["markets"]["CAPITAL_GOODS"]["series"]
        benchmark = payload["markets"]["NIFTY_50"]["series"]
        self.assertEqual(benchmark[0]["normalized_value"], 100.0)
        self.assertEqual(benchmark[-1]["relative_to_nifty50"], 100.0)
        self.assertGreater(capital[-1]["normalized_value"], 100.0)
        self.assertGreater(capital[-1]["return"], 0.0)
        self.assertNotIn("CAPITAL_GOODS_VS_FMCG", payload["markets"])

    def test_lag_analysis_has_fixed_registered_windows(self):
        market = build_sector_performance_payload(self.prices, self.definitions)
        execution = {
            "series": {
                "capex_actual": {
                    "values": [
                        {"date": f"{year}-03-31", "value": value}
                        for year, value in zip(range(2018, 2025), [100, 110, 125, 150, 190, 240, 300])
                    ]
                }
            }
        }
        payload, estimates = build_lag_analysis(execution, market)
        validate_payload(payload, "dated_multi_series.schema.json")
        self.assertEqual(len(payload["series"]), 43)
        self.assertIn("nifty_50_lead_3m", payload["series"])
        self.assertIn("capital_goods_vs_fmcg_lag_0m", payload["series"])
        self.assertEqual(estimates["nifty_50_lead_6m"]["direction"], "market_leads")
        self.assertTrue(all("_lag_" in key or "_lead_" in key for key in estimates))
        self.assertTrue(all(item["n"] >= 0 for item in estimates.values()))


class CorporateFundamentalsTests(unittest.TestCase):
    def test_company_growth_is_aggregated_as_group_median(self):
        records = []
        for group, keys in (("capital_goods", ("A", "B")), ("infrastructure", ("C", "D"))):
            for key in keys:
                records.extend([
                    CorporateFundamental(key, key, group, pd.Timestamp("2023-03-31"), 100, 20, 10, 50, 25, 12),
                    CorporateFundamental(key, key, group, pd.Timestamp("2024-03-31"), 110, 24, 12, 55, 24, 14),
                ])
        payload = build_corporate_fundamentals_payload(tuple(records))
        validate_payload(payload, "dated_multi_series.schema.json")
        values = payload["series"]["capital_goods_revenue_growth"]["values"]
        self.assertAlmostEqual(values[-1]["value"], 10.0)


class CapexSummaryTests(unittest.TestCase):
    def test_reverse_market_leads_do_not_drive_sector_transmission_verdict(self):
        execution = {"series": {
            "actual_capex_pct_gdp": {"values": [{"value": 1}, {"value": 2}]},
            "actual_capex_pct_total_expenditure": {"values": [{"value": 4}, {"value": 8}]},
        }}
        private = {"series": {
            "private_corporate_gfcf_pct_gdp": {"values": [{"value": 10}, {"value": 11}]},
            "manufacturing_capacity_utilisation": {"values": [{"value": 70}, {"value": 72}]},
        }}
        fiscal = {"series": {
            "general_government_debt_pct_gdp": {"values": [{"value": 82}]},
            "interest_payments_pct_revenue": {"values": [{"value": 37}]},
        }}
        estimates = {
            "capital_goods_lead_6m": {
                "pearson": 0.9, "n": 6, "direction": "market_leads",
                "outcome_type": "market", "label": "Nifty Capital Goods",
            },
            "nifty_50_lag_0m": {
                "pearson": 0.8, "n": 6, "direction": "capex_leads",
                "outcome_type": "market", "label": "Nifty 50",
            },
            "capital_goods_lag_0m": {
                "pearson": -0.4, "n": 6, "direction": "capex_leads",
                "outcome_type": "market", "label": "Nifty Capital Goods",
            },
        }
        summary = classify_summary(execution, private, fiscal, estimates)
        sector = next(item for item in summary["hypotheses"] if item["key"] == "sector_transmission")
        self.assertEqual(sector["status"], "inconclusive")


if __name__ == "__main__":
    unittest.main()
