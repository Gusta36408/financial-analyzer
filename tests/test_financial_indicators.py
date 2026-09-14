from unittest import TestCase

from models.financial_models import CompanyData, StandardizedFinancialData, StandardizedNode, StandardizedStatement
from services.analysis_service import calculate_indicators


def node(name, value, *children): return StandardizedNode(name, value, children)
def data(year, at, pl, ll=20):
    bpa = node("TOTAL ATIVO", at, node("ATIVO CIRCULANTE", 100, node("FINANCEIRO", 30, node("Disponível", 10), node("Aplicações de Liquidez e TVM", 20)), node("OPERACIONAL", 70, node("Contas a receber", 40), node("Estoques", 20), node("Outros ativos circulantes", 10))), node("ATIVO NÃO CIRCULANTE", at-100, node("Realizável a L.P. Contas a Receber", 10), node("Realizável a L.P. Estoques", 5), node("Demais Realizáveis a Longo Prazo", 5), node("Investimentos", 10), node("Imobilizado", 40), node("Intangível", at-170)))
    bpp = node("TOTAL PASSIVO + PL", at, node("PASSIVO CIRCULANTE", 80, node("OPERACIONAL", 60, node("Fornecedores", 30), node("Outras Obrigações", 30)), node("FINANCEIRO", 20, node("Empréstimos e Financiamentos", 20))), node("PASSIVO NÃO CIRCULANTE", at-pl-80, node("Empréstimos e Financiamentos", 30), node("Outras Obrigações", at-pl-110)), node("TOTAL CAPITAL DE TERCEIROS", at-pl-0), node("PATRIMÔNIO LÍQUIDO", pl))
    dre = node("DRE", ll, node("RECEITA LÍQUIDA", 200), node("(-) Despesas Financeiras", -10), node("(=) LUCRO OPERAC. I", 50), node("(=) RESULTADO LÍQUIDO DO PERÍODO", ll))
    return StandardizedFinancialData(CompanyData("T", "1"), year, {"BPA": StandardizedStatement("BPA", bpa, (), None, "", "1"), "BPP": StandardizedStatement("BPP", bpp, (), None, "", "1"), "DRE": StandardizedStatement("DRE", dre, (), None, "", "1")})


class IndicatorTests(TestCase):
    def setUp(self): self.result = {(x.code, x.exercise): x for x in calculate_indicators([data(2022, 180, 70), data(2023, 200, 80), data(2024, 220, 90)], (2023, 2024))}
    def value(self, code, year=2024): return self.result[(code, year)].value
    def test_structure_and_liquidity_indicators(self):
        self.assertAlmostEqual(self.value("IPL"), (10+40+50)/90*100)
        self.assertAlmostEqual(self.value("PCT"), (80+50)/90*100)
        self.assertAlmostEqual(self.value("CE"), 80/130*100)
        self.assertAlmostEqual(self.value("EFSAT"), 50/220*100)
        self.assertAlmostEqual(self.value("LG"), 120/130)
        self.assertAlmostEqual(self.value("LC"), 100/80)
        self.assertAlmostEqual(self.value("LS"), 70/80)
    def test_coverage_and_profitability_indicators(self):
        self.assertAlmostEqual(self.value("ICJ"), -5)
        self.assertAlmostEqual(self.value("GA"), 200/210)
        self.assertAlmostEqual(self.value("RSV"), 10)
        self.assertAlmostEqual(self.value("ROA"), 20/210*100)
        self.assertAlmostEqual(self.value("ROE"), 20/((80+90-20)/2)*100)
    def test_first_display_year_uses_internal_previous_year(self):
        self.assertIsNotNone(self.value("GA", 2023))
        self.assertIsNotNone(self.value("ROA", 2023))
        self.assertIsNotNone(self.value("ROE", 2023))
    def test_zero_denominator_is_not_a_number(self):
        zero = {(x.code, x.exercise): x for x in calculate_indicators([data(2022, 180, 70), data(2023, 200, 0)], (2023,))}
        self.assertIsNone(zero[("IPL", 2023)].value)
        self.assertIn("denominador", zero[("IPL", 2023)].status)
