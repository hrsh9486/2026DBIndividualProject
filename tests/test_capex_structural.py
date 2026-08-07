"""Contracts for structural source parsers and in-memory transformations."""

from datetime import date
from io import BytesIO
from pathlib import Path
import sys
import unittest
import zipfile


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from extractors.national_accounts import parse_national_accounts_pdf_text  # noqa: E402
from extractors.rbi_handbook import read_html_table, read_xlsx_sheets  # noqa: E402
from extractors.rbi_obicus import ObicusResponse, parse_obicus_html  # noqa: E402
from extractors.union_budget import UnionBudgetSnapshot, parse_expenditure_pdf_text  # noqa: E402
from models import FiscalPeriod  # noqa: E402
from transforms.private_investment import build_capacity_utilisation_records  # noqa: E402
from transforms.government_investment import build_government_investment_records  # noqa: E402
from validators import validate_payload  # noqa: E402


class FiscalPeriodTests(unittest.TestCase):
    def test_indian_fiscal_year_has_explicit_boundaries(self):
        period = FiscalPeriod(2024)
        self.assertEqual(period.label, "FY2024-25")
        self.assertEqual(period.start_date, date(2024, 4, 1))
        self.assertEqual(period.end_date, date(2025, 3, 31))


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
            source_url=f"https://www.indiabudget.gov.in/budget{edition}/bag6.pdf",
            retrieved_at="2026-07-21T10:00:00+00:00",
            raw_path=Path(f"budget-{edition}.pdf"),
            checksum=str(edition),
        )

    def test_budget_parser_locks_column_meaning(self):
        snapshot = parse_expenditure_pdf_text(
            """
            Expenditure of Government of India
            2024-2025 Actuals 2025-2026 Budget Estimates
            2025-2026 Revised Estimates 2026-2027 Budget Estimates
            Grand Total 4,652,867 5,065,345 4,964,842 5,347,315
            Effective Capital Expenditure of Government
            Capital Expenditure 1,051,953 1,121,090 1,095,755 1,221,821
            """,
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
        records = build_government_investment_records(snapshots)
        execution = {
            record.period_label: record.value
            for record in records
            if record.indicator == "capex_execution_ratio"
        }
        self.assertAlmostEqual(execution["FY2024-25"], 90.0)


class RbiHandbookTests(unittest.TestCase):
    def test_html_reader_selects_the_data_table(self):
        html = """
        <table><tr><td>navigation</td></tr></table>
        <table><tr><th>Year</th><th>Debt</th></tr>
        <tr><td>2023-24</td><td>81.76</td></tr>
        <tr><td>2024-25</td><td>81.92</td></tr></table>
        """
        sheet = read_html_table(html, table_label="Table 239")
        self.assertEqual(sheet.rows[-1], ("2024-25", 81.92))

    def test_xlsx_reader_preserves_sparse_cells_and_types(self):
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
        self.assertEqual(sheets[0].rows, (("Month", None, 103.5), ("Apr-2024", None, 104)))


class PrivateInvestmentSourceTests(unittest.TestCase):
    def test_obicus_selects_unadjusted_capacity_utilisation(self):
        html = """
        <table><tr><th>Table 1: Capacity Utilisation</th></tr>
        <tr><th>Quarter</th><th>Number of responding companies</th>
        <th>Capacity Utilisation</th><th>Seasonally Adjusted Capacity Utilisation</th></tr>
        <tr><td>Q4:2024-25</td><td>960</td><td>77.7</td><td>75.5</td></tr>
        <tr><td>Q1:2025-26</td><td>887</td><td>74.1</td><td>75.8</td></tr></table>
        """
        observations = parse_obicus_html(html)
        response = ObicusResponse(
            observations,
            "https://www.rbi.org.in/scripts/PublicationsView.aspx?id=23808",
            "2026-07-21T10:00:00+00:00",
            Path("unused.html"),
            "abc",
        )
        records = build_capacity_utilisation_records(response)
        self.assertEqual(records[0].value, 77.7)
        self.assertEqual(records[0].date, date(2025, 3, 31))

    def test_national_accounts_combines_private_corporate_sectors(self):
        observations = parse_national_accounts_pdf_text("""
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
        """)
        self.assertEqual(observations[0].private_corporate_gfcf_crore, 2_853_357)
        self.assertEqual(observations[-1].total_gfcf_crore, 10_064_927)


if __name__ == "__main__":
    unittest.main()
