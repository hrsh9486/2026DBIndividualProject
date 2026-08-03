"""Transform, lag, aggregation and time-semantics tests."""

from dataclasses import replace
from datetime import date
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from analysis.alignment import align_registered_inputs  # noqa: E402
from analysis.loader import LoadedObservation, LoadedSeries  # noqa: E402
from config.evidence_specs import (  # noqa: E402
    AlignmentStrategy,
    EVIDENCE_SPECS,
    Transformation,
)
from models import ObservationStatus  # noqa: E402


def loaded_series(name, series_key, values, *, frequency="fiscal_year", statuses=None):
    statuses = statuses or [ObservationStatus.ACTUAL] * len(values)
    dates = [
        date(year, 3, 31)
        for year in range(2020, 2020 + len(values))
    ]
    observations = tuple(
        LoadedObservation(period, value, status, f"FY{period.year - 1}-{str(period.year)[-2:]}")
        for period, value, status in zip(dates, values, statuses)
    )
    return LoadedSeries(
        name=name,
        asset_path="synthetic.json",
        series_key=series_key,
        entity="IND",
        unit="percent",
        frequency=frequency,
        artifact_sha256="0" * 64,
        artifact_generated_at="2026-07-28T10:00:00+00:00",
        artifact_start_date=dates[0],
        artifact_end_date=dates[-1],
        observations=observations,
    )


class EvidenceAlignmentTests(unittest.TestCase):
    def test_difference_and_lag_use_prior_fiscal_period_without_lookahead(self):
        spec = EVIDENCE_SPECS["debt-interest-burden-change"]
        loaded = {
            "interest_burden_change": loaded_series(
                "interest_burden_change", "interest_payments_pct_revenue", [10, 12, 15, 19]
            ),
            "lagged_general_government_debt": loaded_series(
                "lagged_general_government_debt", "general_government_debt_pct_gdp", [70, 72, 74, 76]
            ),
            "lagged_primary_balance": loaded_series(
                "lagged_primary_balance", "primary_balance_pct_gdp", [-3, -2, -1, 0]
            ),
        }
        sample = align_registered_inputs(spec, loaded)
        self.assertEqual([row.date.year for row in sample.rows], [2021, 2022, 2023])
        self.assertEqual(
            sample.rows[0].values,
            {
                "interest_burden_change": 2,
                "lagged_general_government_debt": 70,
                "lagged_primary_balance": -3,
            },
        )
        self.assertEqual(
            sample.rows[0].source_dates["lagged_general_government_debt"],
            date(2020, 3, 31),
        )
        self.assertTrue(
            all(
                source_date <= row.date
                for row in sample.rows
                for source_date in row.source_dates.values()
            )
        )

    def test_disallowed_status_is_counted_and_breaks_a_difference(self):
        spec = EVIDENCE_SPECS["debt-interest-burden-change"]
        loaded = {
            "interest_burden_change": loaded_series(
                "interest_burden_change",
                "interest_payments_pct_revenue",
                [10, 12, 15, 19],
                statuses=[
                    ObservationStatus.ACTUAL,
                    ObservationStatus.PROVISIONAL,
                    ObservationStatus.ACTUAL,
                    ObservationStatus.ACTUAL,
                ],
            ),
            "lagged_general_government_debt": loaded_series(
                "lagged_general_government_debt", "general_government_debt_pct_gdp", [70, 72, 74, 76]
            ),
            "lagged_primary_balance": loaded_series(
                "lagged_primary_balance", "primary_balance_pct_gdp", [-3, -2, -1, 0]
            ),
        }
        sample = align_registered_inputs(spec, loaded)
        self.assertEqual([row.date.year for row in sample.rows], [2023])
        self.assertEqual(sample.excluded["interest_burden_change:status"], 1)
        self.assertEqual(
            sample.excluded["interest_burden_change:difference_unavailable"],
            2,
        )

    def test_monthly_to_quarterly_mean_requires_three_months(self):
        original = EVIDENCE_SPECS["upi-adoption-trend"]
        input_spec = replace(
            original.inputs[0],
            transformation=Transformation.LEVEL,
        )
        spec = replace(
            original,
            inputs=(input_spec,),
            alignment=AlignmentStrategy.MONTHLY_TO_QUARTERLY_MEAN,
            analysis_start_date=None,
        )
        observations = (
            LoadedObservation(date(2024, 1, 31), 1, ObservationStatus.ACTUAL),
            LoadedObservation(date(2024, 2, 29), 2, ObservationStatus.ACTUAL),
            LoadedObservation(date(2024, 3, 31), 3, ObservationStatus.ACTUAL),
            LoadedObservation(date(2024, 4, 30), 4, ObservationStatus.ACTUAL),
        )
        loaded = LoadedSeries(
            name=input_spec.name,
            asset_path="synthetic.json",
            series_key=input_spec.series_key,
            entity="IND",
            unit=input_spec.expected_unit,
            frequency="monthly",
            artifact_sha256="0" * 64,
            artifact_generated_at="2026-07-28T10:00:00+00:00",
            artifact_start_date=date(2024, 1, 31),
            artifact_end_date=date(2024, 4, 30),
            observations=observations,
        )
        sample = align_registered_inputs(spec, {input_spec.name: loaded})
        self.assertEqual(len(sample.rows), 1)
        self.assertEqual(sample.rows[0].date, date(2024, 3, 31))
        self.assertEqual(sample.rows[0].values[input_spec.name], 2)
        self.assertEqual(sample.excluded[f"{input_spec.name}:incomplete_quarter"], 1)

    def test_fiscal_join_rejects_calendar_year_dates(self):
        spec = EVIDENCE_SPECS["debt-interest-burden-change"]
        bad = loaded_series(
            "interest_burden_change", "interest_payments_pct_revenue", [10, 12, 15]
        )
        bad = replace(
            bad,
            observations=tuple(
                replace(item, date=date(item.date.year, 12, 31))
                for item in bad.observations
            ),
        )
        loaded = {
            "interest_burden_change": bad,
            "lagged_general_government_debt": loaded_series(
                "lagged_general_government_debt", "general_government_debt_pct_gdp", [70, 72, 74]
            ),
            "lagged_primary_balance": loaded_series(
                "lagged_primary_balance", "primary_balance_pct_gdp", [-3, -2, -1]
            ),
        }
        fiscal_spec = replace(spec, alignment=AlignmentStrategy.FISCAL_YEAR_END_INNER_JOIN)
        with self.assertRaises(ValueError):
            align_registered_inputs(fiscal_spec, loaded)


if __name__ == "__main__":
    unittest.main()
