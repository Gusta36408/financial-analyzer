from unittest import TestCase

from models.financial_models import AnalysisLine, CompanyData, FinancialIndicator, VerticalHorizontalAnalysis
from services.comparison_service import CompanyComparisonInput, comparison_chart_rows, comparison_csv, comparison_rows, difference_rows, generate_comparison_pdf, indicator_rows, validate_inputs


def item(number: int) -> CompanyComparisonInput:
    company = CompanyData(f"Empresa {number}", str(number))
    lines = []
    for year, value in ((2023, 100.0 * number), (2024, 120.0 * number), (2025, 0.0 if number == 2 else 150.0 * number)):
        lines.extend((AnalysisLine("DRE", "RECEITA LÍQUIDA", year, value, 100, None if year == 2023 else 20, None, "BASE_ZERO" if value == 0 else "OK"), AnalysisLine("BPP", "PATRIMÔNIO LÍQUIDO", year, value / 2, 50, None, None, "OK")))
    indicators = tuple(FinancialIndicator(code, code, year, number + year / 10000 if code == "ROA" else number, "%" if code == "ROA" else "vezes", 1, 1, "", "OK") for code in ("IPL", "PCT", "CE", "EFSAT", "LG", "LC", "LS", "ICJ", "GA", "RSV", "ROA", "ROE") for year in (2023, 2024, 2025))
    return CompanyComparisonInput(company, VerticalHorizontalAnalysis((2023, 2024, 2025), tuple(lines)), indicators, ())


class ComparisonTests(TestCase):
    def setUp(self): self.items = tuple(item(index) for index in range(1, 5))
    def test_accepts_two_three_and_four_companies(self):
        self.assertEqual(validate_inputs(self.items[:2]), (2023, 2024, 2025)); self.assertEqual(len(validate_inputs(self.items[:3])), 3); self.assertEqual(len(validate_inputs(self.items)), 3)
    def test_values_use_existing_analysis_lines(self):
        row = next(row for row in comparison_rows(self.items[:2], ("RECEITA LÍQUIDA",)) if row["Exercício"] == 2024)
        self.assertEqual(row["Empresa 1"], 120); self.assertEqual(row["Empresa 2"], 240)
    def test_indicators_use_existing_values(self):
        row = next(row for row in indicator_rows(self.items[:2]) if row["Indicador"] == "ROA" and row["Exercício"] == 2025)
        self.assertEqual(row["Empresa 1"], 1.2025)
    def test_percent_indicator_difference_has_points(self):
        row = difference_rows(self.items[:2], "ROA", 2025, indicator=True)[0]
        self.assertAlmostEqual(row["p.p."], 1); self.assertAlmostEqual(row["Diferença relativa (%)"], 100 / 1.2025)
    def test_monetary_difference_and_base_zero(self):
        row = difference_rows(self.items[:2], "RECEITA LÍQUIDA", 2025)[0]
        self.assertEqual(row["Status"], "OK"); self.assertEqual(row["Diferença absoluta"], -150)
        zero = difference_rows(self.items[1:3], "RECEITA LÍQUIDA", 2025)[0]
        self.assertEqual(zero["Status"], "n/a — base zero"); self.assertIsNone(zero["Diferença relativa (%)"])
    def test_missing_accounts_remain_missing(self):
        row = next(row for row in comparison_rows(self.items[:2], ("Estoques",)) if row["Exercício"] == 2023)
        self.assertIsNone(row["Empresa 1"])
    def test_chart_rows_preserve_years_and_companies(self):
        rows = comparison_chart_rows(self.items[:2], "RECEITA LÍQUIDA")
        self.assertEqual([row["Exercício"] for row in rows], [2023, 2024, 2025]); self.assertIn("Empresa 2", rows[0])
    def test_av_and_ah_fields_are_available_without_recalculation(self):
        av = comparison_rows(self.items[:2], ("RECEITA LÍQUIDA",), "av")
        ah = comparison_rows(self.items[:2], ("RECEITA LÍQUIDA",), "ah")
        self.assertEqual(av[0]["Empresa 1"], 100); self.assertEqual(ah[1]["Empresa 1"], 20)
    def test_csv_is_generated(self):
        content = comparison_csv(self.items[:2])
        self.assertIn(b"Empresa 1", content); self.assertIn(b"ROA", content)
    def test_pdf_is_generated(self):
        pdf = generate_comparison_pdf(self.items[:2])
        self.assertTrue(pdf.startswith(b"%PDF")); self.assertGreater(len(pdf), 1000)
