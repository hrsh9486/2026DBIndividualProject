"""Focused-pipeline contracts, calculations and quality gates."""

from datetime import date
from io import BytesIO
import sys
import unittest
from pathlib import Path
import zipfile


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_digital_integration import build_payload  # noqa: E402
from build_government_investment import build_payload as build_government_payload  # noqa: E402
from builders import build_event_study_payload  # noqa: E402
from config.indicators import Contract  # noqa: E402
from extractors.npci import (  # noqa: E402
    NpciUpiResponse,
    UpiMonthlyRecord,
    parse_upi_api_rows,
    parse_upi_product_statistics,
)
from extractors.gst_revenue import (  # noqa: E402
    AnnualGrossGst,
    GstRevenueResponse,
    GstSourceDocument,
    parse_gst_march_report_text,
    parse_pib_gst_history_text,
)
from extractors.national_accounts import parse_national_accounts_pdf_text  # noqa: E402
from extractors.human_capital import (  # noqa: E402
    parse_aishe_ger_pdf_text,
    parse_plfs_educated_unemployment_pdf_text,
    parse_plfs_regular_salaried_pdf_text,
)
from extractors.nse_institutional_flows import (  # noqa: E402
    InstitutionalFlowDaily,
    NseInstitutionalFlowResponse,
    parse_nse_flow_rows,
)
from extractors.union_budget import UnionBudgetSnapshot, parse_expenditure_pdf_text  # noqa: E402
from extractors.rbi_handbook import read_html_table, read_html_tables, read_xlsx_sheets  # noqa: E402
from extractors.rbi_obicus import ObicusResponse, parse_obicus_html  # noqa: E402
from models import FiscalPeriod, ObservationStatus  # noqa: E402
from transforms.capital_resilience import build_capital_resilience_records  # noqa: E402
from transforms.digital_integration import build_gst_growth_gap_records  # noqa: E402
from transforms.private_investment import build_capacity_utilisation_records  # noqa: E402
from validators import DataQualityError, validate_dated_payload_quality, validate_payload  # noqa: E402


class FiscalPeriodTests(unittest.TestCase):
    def test_indian_fiscal_year_has_explicit_boundaries(self):
        period = FiscalPeriod(2024)
        self.assertEqual(period.label, "FY2024-25")
        self.assertEqual(period.start_date, date(2024, 4, 1))
        self.assertEqual(period.end_date, date(2025, 3, 31))


class NpciExtractionTests(unittest.TestCase):
    def test_parser_ignores_headers_and_normalises_numbers(self):
        html = """
        <table><tr><th>Month</th><th>Banks live</th><th>Volume (Mn)</th><th>Value (Cr)</th></tr>
        <tr><td>January 2024</td><td>550</td><td>12,203.02</td><td>18,41,083.45</td></tr>
        <tr><td>Feb-24</td><td>560</td><td>12,102.00</td><td>18,27,000.00</td></tr></table>
        """
        records = parse_upi_product_statistics(html)
        self.assertEqual([(item.year, item.month) for item in records], [(2024, 1), (2024, 2)])
        self.assertEqual(records[0].banks_live, 550)
        self.assertAlmostEqual(records[0].volume_millions, 12_203.02)
        self.assertAlmostEqual(records[0].value_crore, 1_841_083.45)

    def test_structured_api_rows_use_named_fields(self):
        records = parse_upi_api_rows([{
            "month": "April-2026",
            "no_of_banks_live_on_upi": "713",
            "volume_in_mn": "22,346.8",
            "value_in_cr": "29,029,88.05",
        }])
        self.assertEqual(records[0], UpiMonthlyRecord(
            2026,
            4,
            volume_millions=22_346.8,
            value_crore=2_902_988.05,
            banks_live=713,
        ))


class DigitalIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.upi_records = tuple(
            UpiMonthlyRecord(2024, month, volume_millions=100.0, value_crore=100.0, banks_live=500)
            for month in range(1, 13)
        )
        self.response = NpciUpiResponse(
            records=self.upi_records,
            source_url="https://www.npci.org.in/product/upi/product-statistics",
            retrieved_at="2026-07-21T10:00:00+00:00",
            raw_path=Path("unused.json"),
            checksum="abc",
        )

    def test_bundle_is_schema_valid_and_preserves_missing_gst(self):
        payload = build_payload(
            self.response,
            population_by_year={2024: 1_000_000_000.0},
            nominal_gdp_by_year={2024: 1_000_000_000_000.0},
        )
        validate_payload(payload, Contract.DATED_MULTI_SERIES.value)
        self.assertEqual(payload["series"]["gst_growth_gap"]["values"], [])
        self.assertAlmostEqual(
            payload["series"]["upi_transactions_per_capita"]["values"][0]["value"],
            0.1,
        )
        self.assertAlmostEqual(
            payload["series"]["average_upi_transaction_value"]["values"][0]["value"],
            10.0,
        )
        upi_gdp = payload["series"]["upi_value_pct_gdp"]["values"]
        self.assertIsNone(upi_gdp[10]["value"])
        self.assertAlmostEqual(upi_gdp[11]["value"], 1.2)

    def test_required_series_cannot_be_all_null(self):
        payload = build_payload(
            self.response,
            population_by_year={2024: 1_000_000_000.0},
            nominal_gdp_by_year={2024: 1_000_000_000_000.0},
        )
        with self.assertRaises(DataQualityError):
            validate_dated_payload_quality(payload, required_non_empty=("gst_growth_gap",))

    def test_official_gst_parsers_and_growth_gap(self):
        history = parse_pib_gst_history_text("""
            In the fiscal year 2020-21, the total collection was 11.37 lakh crores.
            collections reaching 14.83 lakh crores in 2021-22.
            continued in 2022-23, with total collections of 18.08 lakh crores.
            fiscal year 2023-24, the GST collection has further surged to 20.18 lakh crores.
        """)
        latest = parse_gst_march_report_text(
            "Total Gross GST Revenue 1,78,484 1,96,141 9.9% 20,18,249 22,08,861 9.4%"
        )
        self.assertEqual(history[2020], 1_137_000)
        self.assertEqual(latest, {2023: 2_018_249, 2024: 2_208_861})

        document = GstSourceDocument(
            "GST report", "https://example.test/gst.pdf", "2026-07-21T10:00:00+00:00",
            Path("unused.pdf"), "abc",
        )
        response = GstRevenueResponse((
            AnnualGrossGst(2023, 2_000_000, ObservationStatus.ACTUAL, document.source_url, document.retrieved_at),
            AnnualGrossGst(2024, 2_200_000, ObservationStatus.PROVISIONAL, document.source_url, document.retrieved_at),
        ), (document,))
        records = build_gst_growth_gap_records(
            response,
            nominal_gdp_by_fiscal_year={
                2023: (30_000_000, ObservationStatus.REVISED),
                2024: (33_000_000, ObservationStatus.PROVISIONAL),
            },
        )
        self.assertEqual(len(records), 1)
        self.assertAlmostEqual(records[0].value, 0.0)
        self.assertEqual(records[0].date, date(2025, 3, 31))
        self.assertEqual(records[0].status, ObservationStatus.PROVISIONAL)


class GovernmentInvestmentTests(unittest.TestCase):
    @staticmethod
    def snapshot(
        edition: int,
        *,
        actual_capex: float,
        prior_budget_capex: float,
        prior_revised_capex: float,
        current_budget_capex: float,
        actual_total: float,
    ) -> UnionBudgetSnapshot:
        return UnionBudgetSnapshot(
            edition_start_year=edition,
            actual_capex=actual_capex,
            prior_budget_capex=prior_budget_capex,
            prior_revised_capex=prior_revised_capex,
            current_budget_capex=current_budget_capex,
            actual_total_expenditure=actual_total,
            prior_budget_total_expenditure=actual_total,
            prior_revised_total_expenditure=actual_total,
            current_budget_total_expenditure=actual_total,
            source_url=f"https://www.indiabudget.gov.in/budget{edition}-{str(edition + 1)[-2:]}/bag6.pdf",
            retrieved_at="2026-07-21T10:00:00+00:00",
            raw_path=Path(f"budget-{edition}.pdf"),
            checksum=str(edition),
        )

    def test_pdf_text_parser_locks_column_meaning(self):
        text = """
        Expenditure of Government of India
        2024-2025 Actuals 2025-2026 Budget Estimates
        2025-2026 Revised Estimates 2026-2027 Budget Estimates
        Grand Total 4,652,867 5,065,345 4,964,842 5,347,315
        Effective Capital Expenditure of Government
        Capital Expenditure 1,051,953 1,121,090 1,095,755 1,221,821
        """
        snapshot = parse_expenditure_pdf_text(
            text,
            edition_start_year=2026,
            source_url="https://www.indiabudget.gov.in/doc/Budget_at_Glance/bag6.pdf",
            retrieved_at="2026-07-21T10:00:00+00:00",
            raw_path=Path("bag6.pdf"),
            checksum="abc",
        )
        self.assertEqual(snapshot.actual_capex, 1_051_953)
        self.assertEqual(snapshot.prior_revised_capex, 1_095_755)
        self.assertEqual(snapshot.current_budget_total_expenditure, 5_347_315)

    def test_vintages_produce_execution_and_actual_share(self):
        snapshots = (
            self.snapshot(2024, actual_capex=70, prior_budget_capex=75, prior_revised_capex=78, current_budget_capex=100, actual_total=800),
            self.snapshot(2025, actual_capex=80, prior_budget_capex=100, prior_revised_capex=110, current_budget_capex=120, actual_total=900),
            self.snapshot(2026, actual_capex=90, prior_budget_capex=120, prior_revised_capex=115, current_budget_capex=130, actual_total=1_000),
        )
        payload = build_government_payload(snapshots)
        validate_payload(payload, Contract.DATED_MULTI_SERIES.value)
        execution = {
            row["period_label"]: row["value"]
            for row in payload["series"]["capex_execution_ratio"]["values"]
        }
        actual_share = {
            row["period_label"]: row["value"]
            for row in payload["series"]["actual_capex_pct_total_expenditure"]["values"]
        }
        self.assertAlmostEqual(execution["FY2024-25"], 90.0)
        self.assertAlmostEqual(actual_share["FY2024-25"], 9.0)
        self.assertEqual(payload["series"]["actual_capex_pct_gdp"]["values"], [])


class RbiHandbookTests(unittest.TestCase):
    def test_html_reader_selects_data_table_and_parses_status_values(self):
        html = """
        <table><tr><td>navigation</td></tr></table>
        <table>
          <tr><th>Year</th><th>Debt</th></tr>
          <tr><td>2023-24</td><td>81.76</td></tr>
          <tr><td>2024-25</td><td>81.92</td></tr>
        </table>
        """
        sheet = read_html_table(html, table_label="Table 239")
        self.assertEqual(sheet.rows[-1], ("2024-25", 81.92))
        self.assertEqual(len(read_html_tables(html, table_label="Table 239")), 1)

    def test_dependency_free_xlsx_reader_preserves_sparse_cells_and_types(self):
        target = BytesIO()
        with zipfile.ZipFile(target, "w") as archive:
            archive.writestr("xl/workbook.xml", """<?xml version="1.0"?>
                <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
                 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
                  <sheets><sheet name="Table" sheetId="1" r:id="rId1"/></sheets>
                </workbook>""")
            archive.writestr("xl/_rels/workbook.xml.rels", """<?xml version="1.0"?>
                <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                  <Relationship Id="rId1" Target="worksheets/sheet1.xml"/>
                </Relationships>""")
            archive.writestr("xl/sharedStrings.xml", """<?xml version="1.0"?>
                <sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
                  <si><t>Month</t></si><si><t>Apr-2024</t></si>
                </sst>""")
            archive.writestr("xl/worksheets/sheet1.xml", """<?xml version="1.0"?>
                <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
                  <sheetData>
                    <row r="1"><c r="A1" t="s"><v>0</v></c><c r="C1"><v>103.5</v></c></row>
                    <row r="2"><c r="A2" t="s"><v>1</v></c><c r="C2"><v>104</v></c></row>
                  </sheetData>
                </worksheet>""")
        sheets = read_xlsx_sheets(target.getvalue())
        self.assertEqual(sheets[0].name, "Table")
        self.assertEqual(sheets[0].rows, (("Month", None, 103.5), ("Apr-2024", None, 104)))


class ObicusTests(unittest.TestCase):
    def test_parser_selects_unadjusted_capacity_utilisation(self):
        html = """
        <table>
          <tr><th>Table 1: Capacity Utilisation</th></tr>
          <tr><th>Quarter</th><th>Number of responding companies</th>
              <th>Capacity Utilisation</th><th>Seasonally Adjusted Capacity Utilisation</th></tr>
          <tr><td>Q4:2024-25</td><td>960</td><td>77.7</td><td>75.5</td></tr>
          <tr><td>Q1:2025-26</td><td>887</td><td>74.1</td><td>75.8</td></tr>
        </table>
        """
        observations = parse_obicus_html(html)
        self.assertEqual(observations[0].capacity_utilisation, 77.7)
        self.assertEqual(observations[0].seasonally_adjusted_capacity_utilisation, 75.5)
        response = ObicusResponse(
            observations,
            "https://www.rbi.org.in/scripts/PublicationsView.aspx?id=23808",
            "2026-07-21T10:00:00+00:00",
            Path("unused.html"),
            "abc",
        )
        records = build_capacity_utilisation_records(response)
        self.assertEqual([item.date for item in records], [date(2025, 3, 31), date(2025, 6, 30)])
        self.assertEqual(records[0].period_label, "Q4:FY2024-25")
        self.assertEqual(records[0].value, 77.7)


class NationalAccountsTests(unittest.TestCase):
    def test_statement_parser_combines_private_corporate_sectors(self):
        text = """
        Statement 1.1 B
        S.No. Item 2022-23 2023-24 2024-25
        3 Gross Domestic Product (GDP) 26,117,627 28,983,909 31,807,309
        Statement 1.2 B
        Statement 7.1 B
        S.No. Item 2022-23 2023-24 2024-25
        Gross Fixed Capital Formation 8,453,506 9,245,752 10,064,927
        2 Private non-financial corporations 2,760,639 2,870,472 3,110,030
        4 Private financial corporations 92,718 102,873 132,521
        Statement 7.2 B
        """
        observations = parse_national_accounts_pdf_text(text)
        self.assertEqual([item.fiscal_start_year for item in observations], [2022, 2023, 2024])
        self.assertEqual(observations[0].private_corporate_gfcf_crore, 2_853_357)
        self.assertEqual(observations[-1].total_gfcf_crore, 10_064_927)


class HumanCapitalTests(unittest.TestCase):
    def test_aishe_parser_selects_both_sexes_all_category_column(self):
        rows = " ".join(
            f"{year}-{str(year + 1)[-2:]} {male} {female} {both} 20 21 22 10 11 12"
            for year, male, female, both in (
                (2023, 28.9, 31.2, 30.0),
                (2022, 28.9, 30.2, 29.5),
                (2021, 28.3, 28.5, 28.4),
                (2020, 26.7, 27.9, 27.3),
                (2019, 24.8, 26.4, 25.6),
            )
        )
        parsed = parse_aishe_ger_pdf_text(
            "Table 47. Gross Enrollment Ratio (GER) Trends Over the Last 5 Years " + rows
        )
        self.assertEqual([(item.year, item.value) for item in parsed], [
            (2019, 25.6), (2020, 27.3), (2021, 28.4), (2022, 29.5), (2023, 30.0),
        ])

    def test_plfs_parsers_lock_combined_person_denominators(self):
        employment = " ".join(
            f"PLFS {year} rural male 1 2 3 4 5 100 rural +urban person 40 16 56 {value} 20 100"
            for year, value in ((2025, 23.6), (2024, 22.4), (2023, 21.5), (2022, 20.9))
        )
        unemployment = " ".join(
            f"PLFS {year} secondary & above 1 2 3 4 5 6 7 8 {value}"
            for year, value in ((2025, 6.5), (2024, 7.0), (2023, 7.0), (2022, 8.0))
        )
        salaried = parse_plfs_regular_salaried_pdf_text(
            "Statement 7: Percentage distribution of workers " + employment
            + " 2025 refers to the period"
        )
        educated = parse_plfs_educated_unemployment_pdf_text(
            "Statement 17: Unemployment rates " + unemployment
            + " 2025 refers to the period"
        )
        self.assertEqual([item.value for item in salaried], [20.9, 21.5, 22.4, 23.6])
        self.assertEqual([item.value for item in educated], [8.0, 7.0, 7.0, 6.5])


class CapitalResilienceTests(unittest.TestCase):
    def test_nse_parser_reconciles_and_normalises_categories(self):
        parsed = parse_nse_flow_rows([
            {"date": "21-Jul-2026", "category": "DII", "buyValue": "1,200", "sellValue": "1,000", "netValue": "200"},
            {"date": "21-Jul-2026", "category": "FII/FPI", "buyValue": "900", "sellValue": "1,100", "netValue": "-200"},
        ])
        self.assertEqual([(item.category, item.net_crore) for item in parsed], [("DII", 200), ("FPI", -200)])

    def test_monthly_transform_requires_complete_rolling_window(self):
        observations = []
        for month in range(1, 13):
            observation_date = date(2025, month, 28)
            observations.extend((
                InstitutionalFlowDaily(observation_date, "DII", 110, 100, 10),
                InstitutionalFlowDaily(observation_date, "FPI", 90, 100, -10),
            ))
        response = NseInstitutionalFlowResponse(
            tuple(observations),
            "https://www.nseindia.com/api/fiidiiTradeReact",
            "2026-07-21T10:00:00+00:00",
            Path("unused.json"),
            "abc",
        )
        records = build_capital_resilience_records(response)
        rolling = [item for item in records if item.indicator == "dii_rolling_12m"]
        ratios = [item for item in records if item.indicator == "dii_offset_ratio"]
        self.assertIsNone(rolling[10].value)
        self.assertEqual(rolling[11].value, 120)
        self.assertTrue(all(item.value == 1 for item in ratios))


class EventStudyTests(unittest.TestCase):
    def test_event_study_builder_emits_schema_valid_named_windows(self):
        payload = build_event_study_payload(
            ({
                "event_id": "covid-2020",
                "label": "COVID-19 global market shock",
                "start_date": "2020-02-19",
                "end_date": "2020-03-23",
                "fpi_net_flow": -60_000.0,
                "dii_net_flow": 55_000.0,
                "dii_offset_ratio": 0.9167,
                "nifty_max_drawdown": -0.38,
                "recovery_days": 228,
            },),
            sources=({"name": "NSE"},),
            methodology="Pre-registered windows aggregated without post-hoc selection.",
        )
        validate_payload(payload, Contract.EVENT_STUDY.value)
        self.assertEqual(payload["metadata"]["event_order"], ["covid-2020"])

    def test_event_study_rejects_reversed_window(self):
        with self.assertRaises(ValueError):
            build_event_study_payload(
                ({"event_id": "bad-window", "start_date": "2022-02-01", "end_date": "2022-01-01"},),
                sources=({"name": "test"},),
                methodology="test",
            )


if __name__ == "__main__":
    unittest.main()
