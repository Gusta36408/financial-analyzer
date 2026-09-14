"""Agrupa resultados individuais já calculados para comparação objetiva."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import BytesIO, StringIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from models.financial_models import CompanyData, EvolutionComparison, FinancialIndicator, VerticalHorizontalAnalysis


ABSOLUTE_ACCOUNTS = (
    "TOTAL ATIVO", "ATIVO CIRCULANTE", "ATIVO NÃO CIRCULANTE", "Disponível", "Aplicações de Liquidez e TVM", "Contas a receber", "Estoques", "Investimentos", "Imobilizado", "Intangível",
    "TOTAL PASSIVO + PL", "PASSIVO CIRCULANTE", "PASSIVO NÃO CIRCULANTE", "TOTAL CAPITAL DE TERCEIROS", "PATRIMÔNIO LÍQUIDO", "Empréstimos e Financiamentos",
    "RECEITA LÍQUIDA", "(=) LUCRO BRUTO", "(=) LUCRO OPERAC. I", "(=) LUCRO OPERAC. II", "(=) LUCRO OPERAC. III", "(=) RESULTADO LÍQUIDO DO PERÍODO",
)
AV_AH_ACCOUNTS = ("Estoques", "Imobilizado", "Disponível", "TOTAL CAPITAL DE TERCEIROS", "PATRIMÔNIO LÍQUIDO", "(-) Custo dos Prod. Vend.", "(=) LUCRO BRUTO", "(=) RESULTADO LÍQUIDO DO PERÍODO")
INDICATOR_CODES = ("IPL", "PCT", "CE", "EFSAT", "LG", "LC", "LS", "ICJ", "GA", "RSV", "ROA", "ROE")


@dataclass(frozen=True)
class CompanyComparisonInput:
    company: CompanyData
    analysis: VerticalHorizontalAnalysis
    indicators: tuple[FinancialIndicator, ...]
    evolution: tuple[EvolutionComparison, ...]


def validate_inputs(items: tuple[CompanyComparisonInput, ...]) -> tuple[int, ...]:
    if not 2 <= len(items) <= 5:
        raise ValueError("Selecione de 2 a 5 empresas para comparar.")
    exercises = items[0].analysis.exercises
    if any(item.analysis.exercises != exercises for item in items[1:]):
        raise ValueError("As empresas não possuem os mesmos exercícios disponíveis para comparação.")
    return exercises


def comparison_rows(items: tuple[CompanyComparisonInput, ...], accounts: tuple[str, ...] = ABSOLUTE_ACCOUNTS, field: str = "va") -> list[dict]:
    exercises = validate_inputs(items); rows = []
    for account in accounts:
        for year in exercises:
            row = {"Item": account, "Exercício": year}
            for item in items:
                line = next((line for line in item.analysis.lines if line.category == account and line.exercise == year), None)
                row[item.company.company_name] = getattr(line, field) if line else None
            rows.append(row)
    return rows


def indicator_rows(items: tuple[CompanyComparisonInput, ...]) -> list[dict]:
    exercises = validate_inputs(items); rows = []
    for code in INDICATOR_CODES:
        for year in exercises:
            row = {"Indicador": code, "Exercício": year}
            for item in items:
                indicator = next((value for value in item.indicators if value.code == code and value.exercise == year), None)
                row[item.company.company_name] = indicator.value if indicator else None
            rows.append(row)
    return rows


def difference_rows(items: tuple[CompanyComparisonInput, ...], account: str, exercise: int, indicator: bool = False) -> list[dict]:
    """Diferenças do primeiro participante contra os demais, sem juízo de valor."""
    rows = indicator_rows(items) if indicator else comparison_rows(items, (account,))
    source = next(row for row in rows if row["Exercício"] == exercise and row.get("Indicador", row.get("Item")) == account)
    first = items[0].company.company_name; base = source[first]; result = []
    for item in items[1:]:
        current = source[item.company.company_name]
        absolute = None if base is None or current is None else current - base
        relative = None if absolute is None or base == 0 else (current / base - 1) * 100
        unit = next((x.unit for x in items[0].indicators if indicator and x.code == account and x.exercise == exercise), "")
        result.append({"Item": account, "Exercício": exercise, "Base": first, "Empresa": item.company.company_name, "Diferença absoluta": absolute, "Diferença relativa (%)": relative, "p.p.": absolute if unit == "%" else None, "Status": "n/a — base zero" if base == 0 else "OK"})
    return result


def comparison_csv(items: tuple[CompanyComparisonInput, ...]) -> bytes:
    rows = comparison_rows(items) + indicator_rows(items)
    columns = sorted({key for row in rows for key in row})
    output = StringIO(); writer = csv.DictWriter(output, fieldnames=columns); writer.writeheader(); writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")


def comparison_chart_rows(items: tuple[CompanyComparisonInput, ...], account: str, indicator: bool = False) -> list[dict]:
    rows = indicator_rows(items) if indicator else comparison_rows(items, (account,))
    label = "Indicador" if indicator else "Item"
    return [{"Exercício": row["Exercício"], **{item.company.company_name: row[item.company.company_name] for item in items}} for row in rows if row[label] == account]


def generate_comparison_pdf(items: tuple[CompanyComparisonInput, ...]) -> bytes:
    exercises = validate_inputs(items); styles = getSampleStyleSheet(); buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=1.2*cm, rightMargin=1.2*cm, topMargin=1.2*cm, bottomMargin=1.2*cm)
    story = [Paragraph("COMPARAÇÃO ENTRE EMPRESAS", styles["Title"]), Paragraph("Empresas: " + "; ".join(item.company.company_name for item in items), styles["Normal"]), Paragraph("Exercícios: " + ", ".join(map(str, exercises)) + " | Fonte: dados estruturados da CVM", styles["Normal"]), Spacer(1, .3*cm)]
    for title, rows in (("Valores absolutos", comparison_rows(items)), ("Indicadores", indicator_rows(items))):
        story.extend([Paragraph(title, styles["Heading2"]), _table(rows, items), Spacer(1, .25*cm)])
    story.append(Paragraph("Observações técnicas: valores ausentes permanecem n/a. Percentuais e índices preservam suas unidades; não há diagnóstico, ranking ou recomendação.", styles["Normal"]))
    doc.build(story)
    return buffer.getvalue()


def _table(rows: list[dict], items: tuple[CompanyComparisonInput, ...]) -> Table:
    labels = ["Item", "Exercício"] if "Item" in rows[0] else ["Indicador", "Exercício"]
    headers = labels + [item.company.company_name for item in items]
    values = [headers] + [[row.get(column, "n/a") if row.get(column) is not None else "n/a" for column in headers] for row in rows]
    width = landscape(A4)[0] - 2.4*cm
    table = Table(values, repeatRows=1, colWidths=[width / len(headers)] * len(headers))
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e78")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .25, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 6), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f6f9")])]))
    return table
