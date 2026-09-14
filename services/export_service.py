"""Exporta dados já processados, sem introduzir cálculos financeiros."""

from __future__ import annotations

import csv
from datetime import datetime
from io import BytesIO, StringIO
from unicodedata import normalize
from zipfile import ZIP_DEFLATED, ZipFile

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.lineplots import LinePlot

from models.financial_models import CvmFinancialData, EvolutionComparison, FinancialIndicator, VerticalHorizontalAnalysis


def csv_exports(analysis: VerticalHorizontalAnalysis, indicators: tuple[FinancialIndicator, ...], comparisons: tuple[EvolutionComparison, ...]) -> dict[str, bytes]:
    """Retorna os cinco CSVs solicitados usando somente valores existentes."""
    return {
        "ativo.csv": _analysis_csv(analysis, "BPA"), "passivo_pl.csv": _analysis_csv(analysis, "BPP"),
        "dre.csv": _analysis_csv(analysis, "DRE"), "indicadores.csv": _indicators_csv(indicators), "variacoes.csv": _comparisons_csv(comparisons),
    }


def csv_zip(exports: dict[str, bytes]) -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, content in exports.items(): archive.writestr(name, content)
    return output.getvalue()


def safe_filename(value: str) -> str:
    """Converte o nome da companhia em componente ASCII seguro para arquivo."""
    ascii_value = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    words = "".join(char if char.isalnum() else " " for char in ascii_value).split()
    return "_".join(words) or "empresa"


def generate_pdf(raw: CvmFinancialData, analysis: VerticalHorizontalAnalysis, indicators: tuple[FinancialIndicator, ...], comparisons: tuple[EvolutionComparison, ...]) -> bytes:
    """Gera PDF tabular, objetivo e paginado a partir das camadas existentes."""
    buffer = BytesIO(); styles = getSampleStyleSheet()
    document = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=1.2*cm, rightMargin=1.2*cm, topMargin=1.2*cm, bottomMargin=1.2*cm)
    identification = f"Empresa: {raw.company.company_name} | Código CVM: {raw.company.cvm_code}"
    if raw.company.cnpj:
        identification += f" | CNPJ: {raw.company.cnpj}"
    story = [Paragraph("ANÁLISE FINANCEIRA", styles["Title"]), Paragraph(identification, styles["Normal"]), Paragraph(f"Exercícios: {', '.join(map(str, analysis.exercises))} | Fonte: Dados estruturados da CVM", styles["Normal"]), Paragraph(f"Data de geração: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["Normal"]), Spacer(1, .4*cm)]
    for statement, title in (("BPA", "1. ATIVO"), ("BPP", "2. PASSIVO + PL"), ("DRE", "3. DRE")):
        story.extend([Paragraph(title, styles["Heading2"]), _table(_analysis_rows(analysis, statement)), Spacer(1, .3*cm)])
    story.extend([Paragraph("4. INDICADORES", styles["Heading2"]), _table(_indicator_rows(indicators)), Spacer(1,.3*cm), Paragraph("5. VARIAÇÕES E EVOLUÇÃO", styles["Heading2"])])
    latest = max(analysis.exercises)
    for statement, title in (("BPA", "Ativo"), ("BPP", "Passivo + PL"), ("DRE", "DRE"), ("INDICATOR", "Indicadores")):
        rows = _comparison_rows([item for item in comparisons if item.statement_type == statement and item.current_exercise == latest])
        story.extend([Paragraph(title, styles["Heading3"]), _table(rows), Spacer(1, .2*cm)])
    story.extend([Paragraph("6. GRÁFICOS", styles["Heading2"])])
    for chart in _report_charts(analysis, indicators):
        story.extend([chart, Spacer(1, .15*cm)])
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def _analysis_csv(analysis, statement):
    return _csv_bytes(["Conta","Exercicio","VA","AV","AH","Variacao_Absoluta","Status_AH"], [[line.category,line.exercise,line.va,line.av,line.ah,line.absolute_change,line.ah_status] for line in analysis.lines if line.statement_type == statement])
def _indicators_csv(indicators): return _csv_bytes(["Indicador","Exercicio","Valor","Unidade","Formula","Status"], [[x.code,x.exercise,x.value,x.unit,x.formula,x.status] for x in indicators])
def _comparisons_csv(comparisons): return _csv_bytes(["Item","Exercicio_Anterior","Exercicio_Atual","Classificacao","Status","Variacao_Absoluta","Variacao_Relativa","Diferenca_PP","Tendencia"], [[x.item,x.previous_exercise,x.current_exercise,x.classification,_status_label(x.status),x.absolute_change,x.relative_change,x.percentage_point_change,x.trend] for x in comparisons])
def _csv_bytes(header, rows):
    stream = StringIO(); writer = csv.writer(stream); writer.writerow(header); writer.writerows(rows); return stream.getvalue().encode("utf-8-sig")
def _analysis_rows(analysis, statement): return [["Conta","Exercício","VA","AV (%)","AH (%)"]] + [[x.category,x.exercise,_money(x.va),_number(x.av),_number(x.ah)] for x in analysis.lines if x.statement_type == statement]
def _indicator_rows(indicators): return [["Indicador","Exercício","Valor","Unidade"]] + [[x.code,x.exercise,_number(x.value),x.unit] for x in indicators]
def _comparison_rows(comparisons): return [["Item","Atual","Situação","Status","Variação abs.","Variação rel.","p.p.","Tendência"]] + [[x.item,x.current_exercise,x.classification,_status_label(x.status),_money(x.absolute_change),_number(x.relative_change),_number(x.percentage_point_change),x.trend] for x in comparisons if x.previous_exercise is not None]
def _money(value): return "" if value is None else f"R$ {value:,.2f}".replace(",","X").replace(".",",").replace("X", ".")
def _number(value): return "n/a" if value is None else f"{value:.2f}"
def _status_label(status): return {"BASE_ZERO": "n/a — base zero", "SIGN_CHANGE": "mudança de sinal"}.get(status, status or "")
def _table(rows):
    available = landscape(A4)[0] - 2.4*cm
    widths = [available * .30] + [available * .70 / (len(rows[0])-1)] * (len(rows[0])-1)
    table = Table(rows, repeatRows=1, colWidths=widths); table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1f4e78")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.25,colors.grey),("FONTSIZE",(0,0),(-1,-1),6),("LEADING",(0,0),(-1,-1),7),("VALIGN",(0,0),(-1,-1),"TOP"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f3f6f9")])]))
    return table
def _footer(canvas, document): canvas.setFont("Helvetica", 8); canvas.drawRightString(28*cm, .7*cm, f"Página {document.page}")

def _line_chart(analysis, category, title, field="va", divisor=1_000_000):
    points = [(line.exercise, getattr(line, field) / divisor) for line in analysis.lines if line.category == category and getattr(line, field) is not None]
    drawing = Drawing(450, 155); drawing.add(String(5, 140, title, fontSize=9))
    if len(points) >= 2:
        chart = LinePlot(); chart.x = 45; chart.y = 20; chart.width = 380; chart.height = 100; chart.data = [points]
        chart.xValueAxis.valueMin = min(point[0] for point in points); chart.xValueAxis.valueMax = max(point[0] for point in points); chart.xValueAxis.valueStep = 1
        minimum, maximum = min(point[1] for point in points), max(point[1] for point in points); padding = max(abs(maximum-minimum)*.1, 1); chart.yValueAxis.valueMin = minimum-padding; chart.yValueAxis.valueMax = maximum+padding
        drawing.add(chart)
    return drawing

def _indicator_chart(indicators, codes, title, suffix):
    points = {code: [(item.exercise, item.value) for item in indicators if item.code == code and item.value is not None] for code in codes}
    points = {code: values for code, values in points.items() if len(values) >= 2}
    drawing = Drawing(450, 165); drawing.add(String(5, 152, title, fontSize=9))
    all_points = [point for values in points.values() for point in values]
    if all_points:
        chart = LinePlot(); chart.x = 45; chart.y = 20; chart.width = 380; chart.height = 105; chart.data = list(points.values())
        years = [point[0] for point in all_points]; values = [point[1] for point in all_points]; chart.xValueAxis.valueMin = min(years); chart.xValueAxis.valueMax = max(years); chart.xValueAxis.valueStep = 1
        padding = max((max(values)-min(values))*.1, .1); chart.yValueAxis.valueMin = min(values)-padding; chart.yValueAxis.valueMax = max(values)+padding
        for index, code in enumerate(points):
            chart.lines[index].strokeColor = (colors.blue, colors.green, colors.orange, colors.red, colors.purple, colors.brown, colors.cyan)[index % 7]
            drawing.add(String(50 + index * 45, 137, code, fontSize=6))
        drawing.add(chart)
    return drawing

def _report_charts(analysis, indicators):
    return (
        _line_chart(analysis, "TOTAL ATIVO", "Estrutura patrimonial - Total Ativo (R$ milhões)"),
        _line_chart(analysis, "TOTAL PASSIVO + PL", "Estrutura patrimonial - Total Passivo + PL (R$ milhões)"),
        _line_chart(analysis, "RECEITA LÍQUIDA", "DRE - Receita Líquida (R$ milhões)"),
        _line_chart(analysis, "(=) RESULTADO LÍQUIDO DO PERÍODO", "DRE - Resultado Líquido do Período (R$ milhões)"),
        _indicator_chart(indicators, ("IPL", "PCT", "CE", "EFSAT", "RSV", "ROA", "ROE"), "Indicadores percentuais (%)", "%"),
        _indicator_chart(indicators, ("LG", "LC", "LS", "ICJ", "GA"), "Indicadores em índice", "vezes"),
        _line_chart(analysis, "ATIVO CIRCULANTE", "Análise Vertical - Ativo Circulante (%)", "av", 1),
        _line_chart(analysis, "TOTAL ATIVO", "Análise Horizontal - Total Ativo (%)", "ah", 1),
    )
