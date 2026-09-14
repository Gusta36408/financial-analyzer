"""Ponto de extensão para a montagem do relatório e geração do PDF."""

from models.financial_models import ReportSection


_REPORT_SECTIONS = (
    ReportSection("Resumo da empresa"),
    ReportSection("Balanço Patrimonial"),
    ReportSection("DRE"),
    ReportSection("Análise Vertical"),
    ReportSection("Análise Horizontal"),
    ReportSection("Indicadores financeiros"),
    ReportSection("Gráficos"),
    ReportSection("Relatório em PDF"),
)


def get_report_sections() -> tuple[ReportSection, ...]:
    """Lista os espaços reservados que serão preenchidos nas próximas etapas."""
    return _REPORT_SECTIONS


def generate_pdf_report(*args: object, **kwargs: object) -> bytes:
    """Reservado para etapa futura: gerar o PDF do relatório."""
    raise NotImplementedError("A geração real de PDF será implementada em uma etapa futura.")
