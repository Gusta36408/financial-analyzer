from unittest import TestCase

from models.financial_models import AnalysisLine, FinancialIndicator, VerticalHorizontalAnalysis
from services.analysis_service import compare_evolution, principal_variations


def line(year, value): return AnalysisLine("BPA", "Conta", year, value, None, None, None, "OK")
def indicator(year, value, unit="%"): return FinancialIndicator("ROA", "ROA", year, value, unit, None, None, "", "OK")


class EvolutionTests(TestCase):
    def test_increase_reduction_and_stability(self):
        result = compare_evolution(VerticalHorizontalAnalysis((2023, 2024, 2025), (line(2023, 100), line(2024, 120), line(2025, 120))), ())
        self.assertEqual(result[1].classification, "Aumento")
        self.assertAlmostEqual(result[1].relative_change, 20)
        self.assertEqual(result[2].classification, "Estável")
    def test_trends_and_extremes(self):
        growth = compare_evolution(VerticalHorizontalAnalysis((2023,2024,2025), (line(2023,1),line(2024,2),line(2025,3))), ())
        self.assertEqual(growth[-1].trend, "crescimento contínuo")
        self.assertEqual(growth[-1].maximum_exercise, 2025)
        oscillation = compare_evolution(VerticalHorizontalAnalysis((2023,2024,2025), (line(2023,1),line(2024,3),line(2025,2))), ())
        self.assertEqual(oscillation[-1].trend, "oscilação")
    def test_zero_and_sign_change(self):
        zero = compare_evolution(VerticalHorizontalAnalysis((2023,2024), (line(2023,0),line(2024,5))), ())
        self.assertEqual(zero[-1].classification, "Novo valor")
        sign = compare_evolution(VerticalHorizontalAnalysis((2023,2024), (line(2023,-5),line(2024,5))), ())
        self.assertEqual(sign[-1].classification, "Mudança de sinal")
    def test_percentage_points_are_separate(self):
        result = compare_evolution(VerticalHorizontalAnalysis((), ()), (indicator(2023, 1.2), indicator(2024, 0.54)))
        comparison = result[-1]
        self.assertAlmostEqual(comparison.percentage_point_change, -0.66)
        self.assertAlmostEqual(comparison.relative_change, -55)
    def test_principal_variations(self):
        result = compare_evolution(VerticalHorizontalAnalysis((2023,2024), (line(2023,100),line(2024,150))), ())
        self.assertEqual(principal_variations(result, 2024, 1)[0].item, "Conta")
