from unittest import TestCase

from models.financial_models import CompanyData, CvmFinancialData, EvolutionComparison, FinancialIndicator, VerticalHorizontalAnalysis, AnalysisLine
from services.export_service import csv_exports, csv_zip, generate_pdf, safe_filename


class ExportTests(TestCase):
    def setUp(self):
        self.raw = CvmFinancialData(CompanyData("Companhia Teste", "123", "00.000.000/0001-00"), 2025, {})
        self.analysis = VerticalHorizontalAnalysis((2024, 2025), tuple(AnalysisLine(statement, "Linha", year, -10 if year == 2024 else 20, 1, None, None, "") for statement in ("BPA", "BPP", "DRE") for year in (2024, 2025)))
        self.indicators = (FinancialIndicator("ROA", "ROA", 2024, 1.2, "%", 1, 2, "(LL / ATm) × 100", "OK"), FinancialIndicator("ROA", "ROA", 2025, .54, "%", 1, 2, "(LL / ATm) × 100", "OK"))
        self.comparisons = (EvolutionComparison("ROA", "INDICATOR", 2025, 2024, .54, 1.2, -.66, -55, -.66, "Redução", "redução contínua", 2024, 2025, "OK"),)
    def test_csvs_and_zip_preserve_structured_values(self):
        exports = csv_exports(self.analysis, self.indicators, self.comparisons)
        self.assertEqual(set(exports), {"ativo.csv", "passivo_pl.csv", "dre.csv", "indicadores.csv", "variacoes.csv"})
        self.assertIn(b"-10", exports["ativo.csv"])
        self.assertIn(b"ROA", exports["indicadores.csv"])
        self.assertTrue(csv_zip(exports).startswith(b"PK"))

    def test_safe_filename_removes_accents_and_unsafe_characters(self):
        self.assertEqual(safe_filename("Magazine Luíza S.A. / 2025"), "magazine_luiza_s_a_2025")

    def test_variations_export_keeps_technical_status(self):
        base_zero = EvolutionComparison("Conta", "BPA", 2025, 2024, 10, 0, 10, None, None, "Novo valor", "crescimento", 2024, 2025, "BASE_ZERO")
        exported = csv_exports(self.analysis, self.indicators, (base_zero,))["variacoes.csv"].decode("utf-8-sig")
        self.assertIn("n/a — base zero", exported)
    def test_pdf_is_generated_with_company_and_sections(self):
        pdf = generate_pdf(self.raw, self.analysis, self.indicators, self.comparisons)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 1000)
