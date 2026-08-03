"""Numerical and registered-estimator tests using synthetic observations only."""

import calendar
from datetime import date
import math
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from analysis.alignment import AlignedRow, AlignedSample  # noqa: E402
from analysis.estimation import (  # noqa: E402
    _estimate_fiscal,
    _estimate_upi,
    _fiscal_design,
)
from analysis.pipeline import PreparedAnalysis  # noqa: E402
from analysis.regression import RegressionError, fit_ols_hac  # noqa: E402
from config.evidence_specs import EVIDENCE_SPECS  # noqa: E402
from models import EligibilityResult, ObservationStatus  # noqa: E402


def eligible(count):
    return EligibilityResult(
        eligible=True,
        required_observations=30,
        available_observations=count,
        reason="Synthetic fixture passed.",
        checks={"synthetic": True},
    )


class EvidenceRegressionTests(unittest.TestCase):
    def test_hac_fit_recovers_synthetic_slope_and_finite_uncertainty(self):
        x = list(range(60))
        dependent = [
            1.5 + 0.7 * value + 0.2 * math.sin(value / 2)
            for value in x
        ]
        fit = fit_ols_hac(
            dependent,
            [[1.0, float(value)] for value in x],
            ("intercept", "slope"),
            max_lags=3,
        )
        low, high = fit.confidence_interval("slope")
        self.assertAlmostEqual(fit.coefficient("slope"), 0.7, places=2)
        self.assertGreater(fit.standard_error("slope"), 0)
        self.assertLess(low, fit.coefficient("slope"))
        self.assertGreater(high, fit.coefficient("slope"))
        self.assertEqual(fit.residual_degrees_of_freedom, 58)

    def test_rank_deficient_design_is_rejected(self):
        with self.assertRaises(RegressionError):
            fit_ols_hac(
                [1.0, 2.0, 3.0, 4.0],
                [[1.0, 1.0, 2.0]] * 4,
                ("intercept", "x", "twice_x"),
                max_lags=1,
            )

    def test_registered_upi_estimator_runs_every_robustness_on_synthetic_data(self):
        spec = EVIDENCE_SPECS["upi-adoption-trend"]
        rows = []
        for index in range(108):
            year = 2017 + (index + 3) // 12
            month = (index + 3) % 12 + 1
            observation_date = date(
                year,
                month,
                calendar.monthrange(year, month)[1],
            )
            post_break = max(
                0,
                (observation_date.year * 12 + observation_date.month)
                - (2020 * 12 + 4),
            )
            logged = (
                -2.0
                + 0.028 * index
                + 0.08 * math.sin(2 * math.pi * month / 12)
                - 0.25 * (observation_date >= date(2020, 4, 30))
                - 0.003 * post_break
                + 0.015 * math.sin(index / 3)
            )
            rows.append(AlignedRow(
                date=observation_date,
                values={"log_upi_transactions_per_capita": logged},
                statuses={
                    "log_upi_transactions_per_capita": ObservationStatus.ACTUAL
                },
                source_dates={
                    "log_upi_transactions_per_capita": observation_date
                },
            ))
        sample = AlignedSample(
            rows=tuple(rows),
            excluded={},
            input_observations={
                "log_upi_transactions_per_capita": len(rows)
            },
        )
        prepared = PreparedAnalysis(
            spec=spec,
            sample=sample,
            eligibility=eligible(len(rows)),
            source_assets=(),
        )
        result = _estimate_upi(prepared)
        focal = next(item for item in result.estimates if item.is_focal)
        self.assertGreater(focal.value, 0)
        self.assertLess(focal.p_value, 0.05)
        self.assertEqual(
            [item.specification for item in result.robustness],
            list(spec.robustness),
        )
        self.assertTrue(all(item.focal_estimate for item in result.robustness))

    def test_registered_fiscal_estimator_preserves_focal_term(self):
        spec = EVIDENCE_SPECS["debt-interest-burden-change"]
        rows = []
        for index, year in enumerate(range(1980, 2025)):
            debt = 65 + 0.18 * index + 4 * math.sin(index / 4)
            primary = -3 + 1.5 * math.cos(index / 5)
            outcome = (
                0.08 * debt
                - 0.12 * primary
                + 0.025 * index
                + 0.08 * math.sin(index / 2)
            )
            observation_date = date(year, 3, 31)
            values = {
                "interest_burden_change": outcome,
                "lagged_general_government_debt": debt,
                "lagged_primary_balance": primary,
            }
            rows.append(AlignedRow(
                date=observation_date,
                values=values,
                statuses={
                    key: ObservationStatus.ACTUAL for key in values
                },
                source_dates={key: observation_date for key in values},
            ))
        sample = AlignedSample(
            rows=tuple(rows),
            excluded={},
            input_observations={key: len(rows) for key in rows[0].values},
        )
        result = _estimate_fiscal(PreparedAnalysis(
            spec=spec,
            sample=sample,
            eligibility=eligible(len(rows)),
            source_assets=(),
        ))
        focal = next(item for item in result.estimates if item.is_focal)
        self.assertEqual(focal.term, spec.focal_terms[0])
        self.assertGreater(focal.value, 0)
        self.assertEqual(
            [item.specification for item in result.robustness],
            list(spec.robustness),
        )

    def test_covid_exclusion_robustness_omits_the_zero_indicator(self):
        spec = EVIDENCE_SPECS["primary-balance-debt-change"]
        rows = tuple(
            AlignedRow(
                date=date(year, 3, 31),
                values={
                    "debt_change": float(year % 5),
                    "lagged_primary_balance": float((year % 7) - 3),
                    "lagged_debt_change": float((year % 4) - 2),
                },
                statuses={
                    "debt_change": ObservationStatus.ACTUAL,
                    "lagged_primary_balance": ObservationStatus.ACTUAL,
                    "lagged_debt_change": ObservationStatus.ACTUAL,
                },
                source_dates={
                    "debt_change": date(year, 3, 31),
                    "lagged_primary_balance": date(year, 3, 31),
                    "lagged_debt_change": date(year, 3, 31),
                },
            )
            for year in range(1985, 2020)
        )
        _, design, terms = _fiscal_design(
            spec,
            rows,
            omit_exceptional_indicator=True,
        )
        self.assertEqual(
            terms,
            ("intercept", "lagged_primary_balance", "lagged_debt_change"),
        )
        self.assertTrue(all(len(row) == len(terms) for row in design))


if __name__ == "__main__":
    unittest.main()
