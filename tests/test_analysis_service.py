from unittest import TestCase

from models.financial_models import CompanyData, StandardizedFinancialData, StandardizedNode, StandardizedStatement
from services.analysis_service import analyze_vertical_horizontal


def sample(year: int, asset: float, cash: float, revenue: float = 100.0) -> StandardizedFinancialData:
    bpa = StandardizedStatement("BPA", StandardizedNode("TOTAL ATIVO", asset, (StandardizedNode("Disponível", cash),)), (), None, "", "1")
    bpp = StandardizedStatement("BPP", StandardizedNode("TOTAL PASSIVO + PL", asset), (), None, "", "1")
    dre = StandardizedStatement("DRE", StandardizedNode("DRE", revenue, (StandardizedNode("RECEITA LÍQUIDA", revenue), StandardizedNode("(-) Custo dos Prod. Vend.", -60.0))), (), None, "", "1")
    return StandardizedFinancialData(CompanyData("Teste", "1"), year, {"BPA": bpa, "BPP": bpp, "DRE": dre})


class AnalysisTests(TestCase):
    def test_av_and_ah(self) -> None:
        result = analyze_vertical_horizontal([sample(2023, 100, 10), sample(2024, 120, 12), sample(2025, 100, 6)])
        lines = [line for line in result.lines if line.category == "Disponível"]
        self.assertEqual(lines[0].av, 10.0)
        self.assertAlmostEqual(lines[1].ah, 20.0)
        self.assertAlmostEqual(lines[2].ah, -50.0)
        self.assertEqual(lines[2].absolute_change, -6)

    def test_zero_and_sign_change(self) -> None:
        zero = analyze_vertical_horizontal([sample(2023, 100, 0), sample(2024, 100, 10)])
        self.assertEqual([line for line in zero.lines if line.category == "Disponível"][1].ah_status, "BASE_ZERO")
        sign = analyze_vertical_horizontal([sample(2023, 100, -10), sample(2024, 100, 10)])
        self.assertEqual([line for line in sign.lines if line.category == "Disponível"][1].ah_status, "SIGN_CHANGE")

    def test_dre_uses_revenue_base(self) -> None:
        result = analyze_vertical_horizontal([sample(2023, 100, 10)])
        cost = next(line for line in result.lines if line.category == "(-) Custo dos Prod. Vend.")
        self.assertEqual(cost.av, -60.0)
