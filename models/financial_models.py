"""Estruturas de domínio preparadas para as próximas etapas."""

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class Company:
    """Representa uma empresa que poderá ser identificada por dados da CVM."""

    name: str
    registration_number: str | None = None

    @property
    def display_name(self) -> str:
        return self.name


@dataclass(frozen=True)
class AnalysisPeriod:
    """Representa o exercício selecionado pelo usuário."""

    year: int


@dataclass
class FinancialStatements:
    """Contêiner para demonstrações padronizadas, ainda sem valores nesta etapa."""

    company: Company
    period: AnalysisPeriod
    balance_sheet: Mapping[str, float] = field(default_factory=dict)
    income_statement: Mapping[str, float] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    """Contêiner futuro para cálculos, gráficos e diagnóstico."""

    statements: FinancialStatements
    metrics: Mapping[str, float] = field(default_factory=dict)
    interpretation: str | None = None


@dataclass(frozen=True)
class ReportSection:
    """Representa uma seção exibida como placeholder no relatório."""

    title: str
    placeholder_message: str = "Em desenvolvimento — disponível em etapas futuras."


@dataclass(frozen=True)
class CompanyData:
    """Identificação cadastral oficial de uma companhia aberta."""

    company_name: str
    cvm_code: str
    cnpj: str | None = None
    registration_status: str | None = None

    @property
    def display_name(self) -> str:
        return f"{self.company_name} — CVM {self.cvm_code}"


@dataclass(frozen=True)
class FinancialAccount:
    """Linha bruta da demonstração, preservando campos fornecidos pela CVM."""

    account_code: str
    account_description: str
    value: float | None
    period: str | None
    raw_fields: Mapping[str, Any]


@dataclass(frozen=True)
class RawFinancialStatement:
    """Uma demonstração DFP ainda não padronizada nem analisada."""

    statement_type: str
    accounts: tuple[FinancialAccount, ...]
    source_file: str
    version: str | None


@dataclass(frozen=True)
class CvmFinancialData:
    """Retorno bruto completo da consulta de uma companhia à CVM."""

    company: CompanyData
    exercise: int
    statements: Mapping[str, RawFinancialStatement]


@dataclass(frozen=True)
class MappingRule:
    """Regra explícita que associa uma conta CVM a uma folha do modelo."""

    statement_type: str
    account_code: str
    category_path: tuple[str, ...]


@dataclass(frozen=True)
class StandardizationAuditEntry:
    """Rastro de cada conta CVM durante o mapeamento."""

    statement_type: str
    account_code: str
    account_description: str
    value: float | None
    period: str | None
    category_path: tuple[str, ...] | None
    status: str
    line_type: str
    reason: str
    original_fields: Mapping[str, Any]


@dataclass(frozen=True)
class StandardizedNode:
    """Nó hierárquico de uma demonstração padronizada."""

    name: str
    value: float | None
    children: tuple["StandardizedNode", ...] = ()


@dataclass(frozen=True)
class TotalValidation:
    """Comparação transparente entre total CVM e total padronizado."""

    cvm_total: float | None
    standardized_total: float
    difference: float | None
    difference_percent: float | None
    is_within_tolerance: bool | None


@dataclass(frozen=True)
class StandardizedStatement:
    """Resultado da padronização de uma demonstração, ainda sem análise."""

    statement_type: str
    root: StandardizedNode | None
    audit_entries: tuple[StandardizationAuditEntry, ...]
    validation: TotalValidation | None
    source_file: str
    version: str | None
    pending_model_message: str | None = None


@dataclass(frozen=True)
class StandardizedFinancialData:
    """Dados CVM transformados em nova estrutura, preservando sua origem."""

    company: CompanyData
    exercise: int
    statements: Mapping[str, StandardizedStatement]


@dataclass(frozen=True)
class AnalysisLine:
    """VA, AV e AH de uma categoria padronizada em um exercício."""
    statement_type: str
    category: str
    exercise: int
    va: float
    av: float | None
    ah: float | None
    absolute_change: float | None
    ah_status: str


@dataclass(frozen=True)
class VerticalHorizontalAnalysis:
    exercises: tuple[int, ...]
    lines: tuple[AnalysisLine, ...]


@dataclass(frozen=True)
class FinancialIndicator:
    code: str
    name: str
    exercise: int
    value: float | None
    unit: str
    numerator: float | None
    denominator: float | None
    formula: str
    status: str


@dataclass(frozen=True)
class EvolutionComparison:
    item: str
    statement_type: str
    current_exercise: int
    previous_exercise: int | None
    current_value: float
    previous_value: float | None
    absolute_change: float | None
    relative_change: float | None
    percentage_point_change: float | None
    classification: str
    trend: str
    maximum_exercise: int
    minimum_exercise: int
    status: str
