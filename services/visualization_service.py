"""Prepara séries descritivas para os gráficos Streamlit, sem recalcular dados."""

from models.financial_models import FinancialIndicator, VerticalHorizontalAnalysis


MONETARY_SERIES = {
    "Estrutura patrimonial": ("TOTAL ATIVO", "TOTAL PASSIVO + PL", "PATRIMÔNIO LÍQUIDO", "TOTAL CAPITAL DE TERCEIROS"),
    "Demonstração do Resultado": ("RECEITA LÍQUIDA", "(=) LUCRO BRUTO", "(=) LUCRO OPERAC. I", "(=) LUCRO OPERAC. II", "(=) LUCRO OPERAC. III", "(=) RESULTADO LÍQUIDO DO PERÍODO"),
}
PERCENT_INDICATORS = ("IPL", "PCT", "CE", "EFSAT", "RSV", "ROA", "ROE")
INDEX_INDICATORS = ("LG", "LC", "LS", "ICJ", "GA")
AV_SERIES = {"Ativo": ("ATIVO CIRCULANTE", "ATIVO NÃO CIRCULANTE"), "Passivo + PL": ("PASSIVO CIRCULANTE", "PASSIVO NÃO CIRCULANTE", "PATRIMÔNIO LÍQUIDO")}
AH_SERIES = ("TOTAL ATIVO", "RECEITA LÍQUIDA", "(=) RESULTADO LÍQUIDO DO PERÍODO", "PATRIMÔNIO LÍQUIDO", "TOTAL CAPITAL DE TERCEIROS")


def analysis_chart_rows(analysis: VerticalHorizontalAnalysis, categories: tuple[str, ...], field: str = "va") -> list[dict]:
    """Converte valores existentes em linhas para os gráficos; ausências ficam ausentes."""
    rows: dict[int, dict] = {year: {"Exercício": year} for year in analysis.exercises}
    for line in analysis.lines:
        if line.category in categories:
            value = getattr(line, field)
            if value is not None:
                rows[line.exercise][line.category] = value
    return list(rows.values())


def indicator_chart_rows(indicators: tuple[FinancialIndicator, ...], codes: tuple[str, ...]) -> list[dict]:
    years = sorted({indicator.exercise for indicator in indicators})
    rows = {year: {"Exercício": year} for year in years}
    for indicator in indicators:
        if indicator.code in codes and indicator.value is not None:
            rows[indicator.exercise][indicator.code] = indicator.value
    return list(rows.values())
