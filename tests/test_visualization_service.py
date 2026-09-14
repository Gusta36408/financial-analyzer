from unittest import TestCase

from models.financial_models import AnalysisLine, FinancialIndicator, VerticalHorizontalAnalysis
from services.visualization_service import analysis_chart_rows, indicator_chart_rows


class VisualizationTests(TestCase):
    def test_monetary_values_and_negative_values_are_preserved(self):
        analysis = VerticalHorizontalAnalysis((2023, 2024), (AnalysisLine("DRE", "Resultado", 2023, -10, -5, None, None, ""), AnalysisLine("DRE", "Resultado", 2024, 20, 10, None, 30, "")))
        rows = analysis_chart_rows(analysis, ("Resultado",))
        self.assertEqual(rows[0]["Resultado"], -10)
        self.assertEqual(rows[1]["Resultado"], 20)

    def test_missing_values_are_not_replaced_by_zero(self):
        analysis = VerticalHorizontalAnalysis((2023, 2024), (AnalysisLine("BPA", "Ativo", 2023, 100, 100, None, None, ""),))
        rows = analysis_chart_rows(analysis, ("Ativo",))
        self.assertNotIn("Ativo", rows[1])

    def test_two_and_three_years_work(self):
        two = VerticalHorizontalAnalysis((2023, 2024), (AnalysisLine("BPA", "Ativo", 2023, 1, 1, None, None, ""), AnalysisLine("BPA", "Ativo", 2024, 2, 2, 100, 1, "")))
        self.assertEqual(len(analysis_chart_rows(two, ("Ativo",))), 2)
        three = VerticalHorizontalAnalysis((2023, 2024, 2025), two.lines + (AnalysisLine("BPA", "Ativo", 2025, 3, 3, 50, 1, ""),))
        self.assertEqual(len(analysis_chart_rows(three, ("Ativo",))), 3)

    def test_indicators_keep_their_units_and_values(self):
        indicators = (FinancialIndicator("ROA", "ROA", 2024, 1.5, "%", 1, 2, "", "OK"), FinancialIndicator("LC", "LC", 2024, 1.2, "vezes", 1, 2, "", "OK"))
        self.assertEqual(indicator_chart_rows(indicators, ("ROA",))[0]["ROA"], 1.5)
        self.assertEqual(indicator_chart_rows(indicators, ("LC",))[0]["LC"], 1.2)
