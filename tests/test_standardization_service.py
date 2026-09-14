"""Testes da padronização, independentes de internet e da interface."""

from unittest import TestCase

from models.financial_models import CompanyData, CvmFinancialData, FinancialAccount, RawFinancialStatement
from services.standardization_service import IGNORED, MAPPED, UNMAPPED, standardize_bpa, standardize_bpp, standardize_dre, standardize_statements


def account(code: str, description: str, value: float) -> FinancialAccount:
    return FinancialAccount(code, description, value, "2025-12-31", {"CD_CONTA": code, "DS_CONTA": description, "VL_CONTA": str(value)})


def bpa(*accounts: FinancialAccount) -> RawFinancialStatement:
    return RawFinancialStatement("BPA", accounts, "dfp_cia_aberta_BPA_con_2025.csv", "2")


class StandardizationServiceTests(TestCase):
    def setUp(self) -> None:
        self.statement = bpa(
            account("1", "Ativo Total", 100.0),
            account("1.01", "Ativo Circulante", 100.0),
            account("1.01.01", "Caixa e Equivalentes de Caixa", 25.0),
            account("1.01.04", "Estoques", 75.0),
            account("1.01.04.01", "Detalhe de estoques", 75.0),
        )

    def test_known_account_maps_to_professor_category(self) -> None:
        result = standardize_bpa(self.statement)
        mapped = next(entry for entry in result.audit_entries if entry.account_code == "1.01.01")
        self.assertEqual(mapped.status, MAPPED)
        self.assertEqual(mapped.category_path[-1], "Disponível")

    def test_unknown_account_is_audited_as_unmapped(self) -> None:
        result = standardize_bpa(bpa(*self.statement.accounts, account("1.01.99", "Conta nova", 2.0)))
        unknown = next(entry for entry in result.audit_entries if entry.account_code == "1.01.99")
        self.assertEqual(unknown.status, UNMAPPED)

    def test_subtotals_and_details_are_explicitly_ignored_not_lost(self) -> None:
        result = standardize_bpa(self.statement)
        statuses = {entry.account_code: entry.status for entry in result.audit_entries}
        self.assertEqual(statuses["1"], IGNORED)
        self.assertEqual(statuses["1.01"], IGNORED)
        self.assertEqual(statuses["1.01.04.01"], IGNORED)
        self.assertEqual(len(result.audit_entries), len(self.statement.accounts))

    def test_preserves_original_raw_fields(self) -> None:
        result = standardize_bpa(self.statement)
        mapped = next(entry for entry in result.audit_entries if entry.account_code == "1.01.04")
        self.assertEqual(mapped.original_fields, self.statement.accounts[3].raw_fields)
        self.assertEqual(self.statement.accounts[3].account_description, "Estoques")

    def test_sums_standardized_assets_and_validates_cvm_total(self) -> None:
        result = standardize_bpa(self.statement)
        self.assertEqual(result.root.value, 100.0)
        self.assertTrue(result.validation.is_within_tolerance)
        self.assertEqual(result.validation.difference, 0.0)

    def test_validation_exposes_unmapped_difference(self) -> None:
        statement = bpa(account("1", "Ativo Total", 110.0), account("1.01.01", "Caixa", 100.0), account("1.01.99", "Conta nova", 10.0))
        result = standardize_bpa(statement)
        self.assertFalse(result.validation.is_within_tolerance)
        self.assertEqual(result.validation.difference, -10.0)

    def test_additional_company_account_is_not_silently_classified(self) -> None:
        result = standardize_bpa(bpa(account("1", "Ativo Total", 1.0), account("1.02.01.11", "Ativo específico", 1.0)))
        self.assertEqual(result.audit_entries[1].status, UNMAPPED)

    def test_version_and_pending_models_are_preserved(self) -> None:
        bpp = RawFinancialStatement("BPP", (account("2", "Passivo", 100.0),), "bpp.csv", "2")
        dre = RawFinancialStatement("DRE", (account("3", "Receita", 100.0),), "dre.csv", "2")
        raw_data = CvmFinancialData(CompanyData("Companhia", "12345"), 2025, {"BPA": self.statement, "BPP": bpp, "DRE": dre})
        result = standardize_statements(raw_data)
        self.assertEqual(result.statements["BPA"].version, "2")
        self.assertIsNotNone(result.statements["BPP"].root)
        self.assertIsNotNone(result.statements["DRE"].root)

    def test_maps_suppliers_loans_and_equity(self) -> None:
        statement = RawFinancialStatement("BPP", (account("2", "Passivo Total", 100.0), account("2.01.02", "Fornecedores", 30.0), account("2.02.01", "Empréstimos", 40.0), account("2.03.01", "Capital", 30.0)), "bpp.csv", "1")
        result = standardize_bpp(statement)
        self.assertTrue(result.validation.is_within_tolerance)
        self.assertEqual(sum(entry.status == MAPPED for entry in result.audit_entries), 3)

    def test_maps_accumulated_profit_loss_to_existing_profit_reserves_category(self) -> None:
        statement = RawFinancialStatement("BPP", (account("2", "Passivo Total", 100.0), account("2.03.05", "Lucros/Prejuízos Acumulados", 100.0)), "bpp.csv", "1")
        result = standardize_bpp(statement)
        entry = next(item for item in result.audit_entries if item.account_code == "2.03.05")
        self.assertEqual(entry.status, MAPPED)
        self.assertEqual(entry.category_path[-1], "Reservas de lucros")
        self.assertTrue(result.validation.is_within_tolerance)

    def test_maps_non_controlling_interest_to_equity_without_forcing_a_subcategory(self) -> None:
        statement = RawFinancialStatement("BPP", (account("2", "Passivo Total", 100.0), account("2.03.09", "Participação dos Acionistas Não Controladores", 100.0)), "bpp.csv", "1")
        result = standardize_bpp(statement)
        entry = next(item for item in result.audit_entries if item.account_code == "2.03.09")
        self.assertEqual(entry.status, MAPPED)
        self.assertEqual(entry.category_path, ("TOTAL PASSIVO + PL", "PATRIMÔNIO LÍQUIDO"))
        self.assertTrue(result.validation.is_within_tolerance)

    def test_calculates_dre_subtotals_with_source_signs(self) -> None:
        statement = RawFinancialStatement("DRE", (account("3.01", "Receita", 100.0), account("3.02", "Custo", -40.0), account("3.04.01", "Vendas", -10.0), account("3.06.01", "Financeira", 5.0), account("3.06.02", "Despesa financeira", -3.0), account("3.11", "Resultado", 52.0)), "dre.csv", "1")
        result = standardize_dre(statement)
        values = {node.name: node.value for node in result.root.children}
        self.assertEqual(values["(=) LUCRO BRUTO"], 60.0)
        self.assertEqual(values["(=) RESULTADO LÍQUIDO DO PERÍODO"], 52.0)
        self.assertTrue(result.validation.is_within_tolerance)
