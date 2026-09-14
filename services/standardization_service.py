"""Padronização auditável dos dados brutos da CVM, sem alterar a origem."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from models.financial_models import (
    CvmFinancialData,
    FinancialAccount,
    MappingRule,
    RawFinancialStatement,
    StandardizationAuditEntry,
    StandardizedFinancialData,
    StandardizedNode,
    StandardizedStatement,
    TotalValidation,
)


MAPPED = "MAPPED"
UNMAPPED = "UNMAPPED"
IGNORED = "IGNORED"
TOTAL_ATIVO_PATH = ("TOTAL ATIVO",)

# Códigos padronizados da estrutura BPA da CVM são o critério primário. Cada
# código foi confirmado nos DFPs reais da Magazine Luiza de 2023 a 2025. Regras
# por descrição devem ser adicionadas somente quando houver validação contábil.
ASSET_MAPPING_RULES = (
    MappingRule("BPA", "1.01.01", ("TOTAL ATIVO", "ATIVO CIRCULANTE", "FINANCEIRO", "Disponível")),
    MappingRule("BPA", "1.01.02", ("TOTAL ATIVO", "ATIVO CIRCULANTE", "FINANCEIRO", "Aplicações de Liquidez e TVM")),
    MappingRule("BPA", "1.01.03", ("TOTAL ATIVO", "ATIVO CIRCULANTE", "OPERACIONAL", "Contas a receber")),
    MappingRule("BPA", "1.01.04", ("TOTAL ATIVO", "ATIVO CIRCULANTE", "OPERACIONAL", "Estoques")),
    MappingRule("BPA", "1.01.05", ("TOTAL ATIVO", "ATIVO CIRCULANTE", "OPERACIONAL", "Outros ativos circulantes")),
    MappingRule("BPA", "1.01.06", ("TOTAL ATIVO", "ATIVO CIRCULANTE", "OPERACIONAL", "Outros ativos circulantes")),
    MappingRule("BPA", "1.01.07", ("TOTAL ATIVO", "ATIVO CIRCULANTE", "OPERACIONAL", "Outros ativos circulantes")),
    MappingRule("BPA", "1.01.08", ("TOTAL ATIVO", "ATIVO CIRCULANTE", "OPERACIONAL", "Outros ativos circulantes")),
    MappingRule("BPA", "1.02.01.01", ("TOTAL ATIVO", "ATIVO NÃO CIRCULANTE", "Demais Realizáveis a Longo Prazo")),
    MappingRule("BPA", "1.02.01.02", ("TOTAL ATIVO", "ATIVO NÃO CIRCULANTE", "Demais Realizáveis a Longo Prazo")),
    MappingRule("BPA", "1.02.01.03", ("TOTAL ATIVO", "ATIVO NÃO CIRCULANTE", "Demais Realizáveis a Longo Prazo")),
    MappingRule("BPA", "1.02.01.04", ("TOTAL ATIVO", "ATIVO NÃO CIRCULANTE", "Realizável a L.P. Contas a Receber")),
    MappingRule("BPA", "1.02.01.05", ("TOTAL ATIVO", "ATIVO NÃO CIRCULANTE", "Realizável a L.P. Estoques")),
    MappingRule("BPA", "1.02.01.06", ("TOTAL ATIVO", "ATIVO NÃO CIRCULANTE", "Demais Realizáveis a Longo Prazo")),
    MappingRule("BPA", "1.02.01.07", ("TOTAL ATIVO", "ATIVO NÃO CIRCULANTE", "Demais Realizáveis a Longo Prazo")),
    MappingRule("BPA", "1.02.01.08", ("TOTAL ATIVO", "ATIVO NÃO CIRCULANTE", "Demais Realizáveis a Longo Prazo")),
    MappingRule("BPA", "1.02.01.09", ("TOTAL ATIVO", "ATIVO NÃO CIRCULANTE", "Demais Realizáveis a Longo Prazo")),
    MappingRule("BPA", "1.02.01.10", ("TOTAL ATIVO", "ATIVO NÃO CIRCULANTE", "Demais Realizáveis a Longo Prazo")),
    MappingRule("BPA", "1.02.02", ("TOTAL ATIVO", "ATIVO NÃO CIRCULANTE", "Investimentos")),
    MappingRule("BPA", "1.02.03", ("TOTAL ATIVO", "ATIVO NÃO CIRCULANTE", "Imobilizado")),
    MappingRule("BPA", "1.02.04", ("TOTAL ATIVO", "ATIVO NÃO CIRCULANTE", "Intangível")),
)

ASSET_HIERARCHY = {
    "TOTAL ATIVO": {
        "ATIVO CIRCULANTE": {
            "FINANCEIRO": ("Disponível", "Aplicações de Liquidez e TVM"),
            "OPERACIONAL": ("Contas a receber", "Estoques", "Outros ativos circulantes"),
        },
        "ATIVO NÃO CIRCULANTE": (
            "Realizável a L.P. Contas a Receber",
            "Realizável a L.P. Estoques",
            "Demais Realizáveis a Longo Prazo",
            "Investimentos",
            "Imobilizado",
            "Intangível",
        ),
    }
}

LIABILITY_RULES = (
    MappingRule("BPP", "2.01.01", ("TOTAL PASSIVO + PL", "PASSIVO CIRCULANTE", "OPERACIONAL", "Outras Obrigações")),
    MappingRule("BPP", "2.01.02", ("TOTAL PASSIVO + PL", "PASSIVO CIRCULANTE", "OPERACIONAL", "Fornecedores")),
    MappingRule("BPP", "2.01.03", ("TOTAL PASSIVO + PL", "PASSIVO CIRCULANTE", "OPERACIONAL", "Outras Obrigações")),
    MappingRule("BPP", "2.01.04", ("TOTAL PASSIVO + PL", "PASSIVO CIRCULANTE", "FINANCEIRO", "Empréstimos e Financiamentos")),
    MappingRule("BPP", "2.01.05", ("TOTAL PASSIVO + PL", "PASSIVO CIRCULANTE", "OPERACIONAL", "Outras Obrigações")),
    MappingRule("BPP", "2.01.06", ("TOTAL PASSIVO + PL", "PASSIVO CIRCULANTE", "OPERACIONAL", "Outras Obrigações")),
    MappingRule("BPP", "2.01.07", ("TOTAL PASSIVO + PL", "PASSIVO CIRCULANTE", "OPERACIONAL", "Outras Obrigações")),
    MappingRule("BPP", "2.02.01", ("TOTAL PASSIVO + PL", "PASSIVO NÃO CIRCULANTE", "Empréstimos e Financiamentos")),
    MappingRule("BPP", "2.02.02", ("TOTAL PASSIVO + PL", "PASSIVO NÃO CIRCULANTE", "Outras Obrigações")),
    MappingRule("BPP", "2.02.03", ("TOTAL PASSIVO + PL", "PASSIVO NÃO CIRCULANTE", "Outras Obrigações")),
    MappingRule("BPP", "2.02.04", ("TOTAL PASSIVO + PL", "PASSIVO NÃO CIRCULANTE", "Outras Obrigações")),
    MappingRule("BPP", "2.02.05", ("TOTAL PASSIVO + PL", "PASSIVO NÃO CIRCULANTE", "Outras Obrigações")),
    MappingRule("BPP", "2.02.06", ("TOTAL PASSIVO + PL", "PASSIVO NÃO CIRCULANTE", "Outras Obrigações")),
    MappingRule("BPP", "2.03.01", ("TOTAL PASSIVO + PL", "PATRIMÔNIO LÍQUIDO", "Capital, Reservas de Capital")),
    MappingRule("BPP", "2.03.02", ("TOTAL PASSIVO + PL", "PATRIMÔNIO LÍQUIDO", "Capital, Reservas de Capital")),
    MappingRule("BPP", "2.03.03", ("TOTAL PASSIVO + PL", "PATRIMÔNIO LÍQUIDO", "Ajustes de Avaliação Patrimonial")),
    MappingRule("BPP", "2.03.04", ("TOTAL PASSIVO + PL", "PATRIMÔNIO LÍQUIDO", "Reservas de lucros")),
    MappingRule("BPP", "2.03.05", ("TOTAL PASSIVO + PL", "PATRIMÔNIO LÍQUIDO", "Reservas de lucros")),
    MappingRule("BPP", "2.03.06", ("TOTAL PASSIVO + PL", "PATRIMÔNIO LÍQUIDO", "Ajustes de Avaliação Patrimonial")),
    MappingRule("BPP", "2.03.07", ("TOTAL PASSIVO + PL", "PATRIMÔNIO LÍQUIDO", "Ajustes de Avaliação Patrimonial")),
    MappingRule("BPP", "2.03.08", ("TOTAL PASSIVO + PL", "PATRIMÔNIO LÍQUIDO", "Ajustes de Avaliação Patrimonial")),
    MappingRule("BPP", "2.03.09", ("TOTAL PASSIVO + PL", "PATRIMÔNIO LÍQUIDO")),
)

DRE_RULES = (
    MappingRule("DRE", "3.01", ("RECEITA LÍQUIDA",)), MappingRule("DRE", "3.02", ("(-) Custo dos Prod. Vend.",)),
    MappingRule("DRE", "3.04.01", ("(-) Despesas com Vendas",)), MappingRule("DRE", "3.04.02", ("(-) Despesas Gerais e Adm.",)),
    MappingRule("DRE", "3.04.03", ("(±) Outras Rec./Desp. Oper.",)), MappingRule("DRE", "3.04.04", ("(±) Outras Rec./Desp. Oper.",)),
    MappingRule("DRE", "3.04.05", ("(±) Outras Rec./Desp. Oper.",)), MappingRule("DRE", "3.04.06", ("(±) Res. da Equivalência Patrimonial",)),
    MappingRule("DRE", "3.06.01", ("(+) Receitas Financeiras",)), MappingRule("DRE", "3.06.02", ("(-) Despesas Financeiras",)),
    MappingRule("DRE", "3.08", ("(-) IR e CS",)), MappingRule("DRE", "3.10", ("(+) Res. Op. descontinuadas",)),
)
DRE_CALCULATED_CVM_CODES = {"3.03", "3.05", "3.07", "3.09", "3.11"}


def standardize_statements(raw_data: CvmFinancialData) -> StandardizedFinancialData:
    """Cria novas demonstrações padronizadas sem modificar ``raw_data``."""
    return StandardizedFinancialData(
        company=raw_data.company,
        exercise=raw_data.exercise,
        statements={
            "BPA": standardize_bpa(raw_data.statements["BPA"]),
            "BPP": standardize_bpp(raw_data.statements["BPP"]),
            "DRE": standardize_dre(raw_data.statements["DRE"]),
        },
    )


def standardize_bpa(statement: RawFinancialStatement) -> StandardizedStatement:
    """Aplica o modelo do professor ao Ativo e registra o destino de cada conta."""
    rules_by_code = {rule.account_code: rule for rule in ASSET_MAPPING_RULES}
    audit = tuple(_audit_account(statement.statement_type, account, rules_by_code) for account in statement.accounts)
    totals = _mapped_totals(audit)
    root = _build_asset_tree(totals)
    cvm_total = next((account.value for account in statement.accounts if account.account_code == "1"), None)
    standardized_total = totals[TOTAL_ATIVO_PATH]
    validation = _validate_total(cvm_total, standardized_total)
    return StandardizedStatement(
        statement_type="BPA",
        root=root,
        audit_entries=audit,
        validation=validation,
        source_file=statement.source_file,
        version=statement.version,
    )


def standardize_bpp(statement: RawFinancialStatement) -> StandardizedStatement:
    audit = tuple(_audit_account("BPP", account, {rule.account_code: rule for rule in LIABILITY_RULES}) for account in statement.accounts)
    totals = _mapped_totals(audit)
    root_name = "TOTAL PASSIVO + PL"
    pc = totals[(root_name, "PASSIVO CIRCULANTE")]; pnc = totals[(root_name, "PASSIVO NÃO CIRCULANTE")]
    pl = totals[(root_name, "PATRIMÔNIO LÍQUIDO")]; third = pc + pnc
    root = StandardizedNode(root_name, pc + pnc + pl, (
        StandardizedNode("PASSIVO CIRCULANTE", pc, (StandardizedNode("OPERACIONAL", totals[(root_name,"PASSIVO CIRCULANTE","OPERACIONAL")], (StandardizedNode("Fornecedores", totals[(root_name,"PASSIVO CIRCULANTE","OPERACIONAL","Fornecedores")]), StandardizedNode("Outras Obrigações", totals[(root_name,"PASSIVO CIRCULANTE","OPERACIONAL","Outras Obrigações")]))), StandardizedNode("FINANCEIRO", totals[(root_name,"PASSIVO CIRCULANTE","FINANCEIRO")], (StandardizedNode("Empréstimos e Financiamentos", totals[(root_name,"PASSIVO CIRCULANTE","FINANCEIRO","Empréstimos e Financiamentos")]),)))),
        StandardizedNode("PASSIVO NÃO CIRCULANTE", pnc, (StandardizedNode("Empréstimos e Financiamentos", totals[(root_name,"PASSIVO NÃO CIRCULANTE","Empréstimos e Financiamentos")]), StandardizedNode("Outras Obrigações", totals[(root_name,"PASSIVO NÃO CIRCULANTE","Outras Obrigações")]))),
        StandardizedNode("TOTAL CAPITAL DE TERCEIROS", third), StandardizedNode("PATRIMÔNIO LÍQUIDO", pl, (StandardizedNode("Capital, Reservas de Capital", totals[(root_name,"PATRIMÔNIO LÍQUIDO","Capital, Reservas de Capital")]), StandardizedNode("Reservas de lucros", totals[(root_name,"PATRIMÔNIO LÍQUIDO","Reservas de lucros")]), StandardizedNode("Ajustes de Avaliação Patrimonial", totals[(root_name,"PATRIMÔNIO LÍQUIDO","Ajustes de Avaliação Patrimonial")]))),
    ))
    return StandardizedStatement("BPP", root, audit, _validate_total(next((a.value for a in statement.accounts if a.account_code == "2"), None), root.value), statement.source_file, statement.version)


def standardize_dre(statement: RawFinancialStatement) -> StandardizedStatement:
    audit = tuple(_audit_account("DRE", account, {rule.account_code: rule for rule in DRE_RULES}) for account in statement.accounts)
    totals = _mapped_totals(audit)
    def value(name: str) -> float: return totals[(name,)]
    gross = value("RECEITA LÍQUIDA") + value("(-) Custo dos Prod. Vend.")
    op1 = gross + value("(-) Despesas com Vendas") + value("(-) Despesas Gerais e Adm.") + value("(±) Outras Rec./Desp. Oper.")
    op2 = op1 + value("(+) Receitas Financeiras") + value("(-) Despesas Financeiras")
    op3 = op2 + value("(±) Res. da Equivalência Patrimonial")
    continued = op3 + value("(-) IR e CS")
    net = continued + value("(+) Valores não recorrentes*") + value("(+) Res. Op. descontinuadas")
    lines = (("RECEITA LÍQUIDA", value("RECEITA LÍQUIDA")), ("(-) Custo dos Prod. Vend.", value("(-) Custo dos Prod. Vend.")), ("(=) LUCRO BRUTO", gross), ("(-) Despesas com Vendas", value("(-) Despesas com Vendas")), ("(-) Despesas Gerais e Adm.", value("(-) Despesas Gerais e Adm.")), ("(±) Outras Rec./Desp. Oper.", value("(±) Outras Rec./Desp. Oper.")), ("(=) LUCRO OPERAC. I", op1), ("(+) Receitas Financeiras", value("(+) Receitas Financeiras")), ("(-) Despesas Financeiras", value("(-) Despesas Financeiras")), ("(=) LUCRO OPERAC. II", op2), ("(±) Res. da Equivalência Patrimonial", value("(±) Res. da Equivalência Patrimonial")), ("(=) LUCRO OPERAC. III", op3), ("(-) IR e CS", value("(-) IR e CS")), ("(=) RES. LÍQ. OPERAÇÕES CONTINUADAS", continued), ("(+) Valores não recorrentes*", value("(+) Valores não recorrentes*")), ("(+) Res. Op. descontinuadas", value("(+) Res. Op. descontinuadas")), ("(=) RESULTADO LÍQUIDO DO PERÍODO", net))
    root = StandardizedNode("DRE", net, tuple(StandardizedNode(name, amount) for name, amount in lines))
    cvm_net = next((a.value for a in statement.accounts if a.account_code == "3.11"), None)
    return StandardizedStatement("DRE", root, audit, _validate_total(cvm_net, net), statement.source_file, statement.version)


def _pending_statement(statement: RawFinancialStatement, message: str) -> StandardizedStatement:
    audit = tuple(
        StandardizationAuditEntry(
            statement_type=statement.statement_type,
            account_code=account.account_code,
            account_description=account.account_description,
            value=account.value,
            period=account.period,
            category_path=None,
            status=UNMAPPED,
            line_type="SOURCE",
            reason="Aguardando estrutura oficial do professor para esta demonstração.",
            original_fields=account.raw_fields,
        )
        for account in statement.accounts
    )
    return StandardizedStatement(statement.statement_type, None, audit, None, statement.source_file, statement.version, message)


def _audit_account(statement_type: str, account: FinancialAccount, rules: dict[str, MappingRule]) -> StandardizationAuditEntry:
    rule = rules.get(account.account_code)
    if rule:
        return _entry(statement_type, account, rule.category_path, MAPPED, "Mapeada por código CVM explícito.")
    if statement_type == "DRE" and account.account_code in DRE_CALCULATED_CVM_CODES:
        return _entry(statement_type, account, None, IGNORED, "Subtotal CVM recalculado na estrutura padronizada.")

    mapped_codes = tuple(rules)
    if any(code.startswith(account.account_code + ".") for code in mapped_codes):
        reason = "Subtotal estrutural da CVM; não é somado para evitar duplicidade."
        return _entry(statement_type, account, None, IGNORED, reason)
    if any(account.account_code.startswith(code + ".") for code in mapped_codes):
        reason = "Detalhamento já incluído na conta CVM mapeada; não é somado para evitar duplicidade."
        return _entry(statement_type, account, None, IGNORED, reason)
    return _entry(statement_type, account, None, UNMAPPED, "Não há regra explícita segura para esta conta CVM.")


def _entry(
    statement_type: str, account: FinancialAccount, category_path: tuple[str, ...] | None, status: str, reason: str
) -> StandardizationAuditEntry:
    return StandardizationAuditEntry(
        statement_type=statement_type,
        account_code=account.account_code,
        account_description=account.account_description,
        value=account.value,
        period=account.period,
        category_path=category_path,
        status=status,
        line_type="SOURCE",
        reason=reason,
        original_fields=account.raw_fields,
    )


def _mapped_totals(entries: Iterable[StandardizationAuditEntry]) -> defaultdict[tuple[str, ...], float]:
    totals: defaultdict[tuple[str, ...], float] = defaultdict(float)
    for entry in entries:
        if entry.status == MAPPED and entry.category_path:
            amount = entry.value or 0.0
            for depth in range(1, len(entry.category_path) + 1):
                totals[entry.category_path[:depth]] += amount
    return totals


def _build_asset_tree(totals: defaultdict[tuple[str, ...], float]) -> StandardizedNode:
    def build(name: str, path: tuple[str, ...], children_definition: object) -> StandardizedNode:
        if isinstance(children_definition, dict):
            children = tuple(build(child, path + (child,), nested) for child, nested in children_definition.items())
        else:
            children = tuple(StandardizedNode(child, totals[path + (child,)]) for child in children_definition)
        return StandardizedNode(name, totals[path], children)

    return build("TOTAL ATIVO", TOTAL_ATIVO_PATH, ASSET_HIERARCHY["TOTAL ATIVO"])


def _validate_total(cvm_total: float | None, standardized_total: float, tolerance: float = 0.01) -> TotalValidation:
    if cvm_total is None:
        return TotalValidation(None, standardized_total, None, None, None)
    difference = standardized_total - cvm_total
    percent = (difference / cvm_total * 100) if cvm_total else None
    return TotalValidation(cvm_total, standardized_total, difference, percent, abs(difference) <= tolerance)
