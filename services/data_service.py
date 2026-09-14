"""Fachada fina que preserva a interface isolada da integração CVM."""

from models.financial_models import CompanyData, CvmFinancialData
from services.cvm_service import CvmService


def get_companies(service: CvmService) -> list[CompanyData]:
    return service.list_companies()


def get_available_periods() -> tuple[int, ...]:
    """Exercícios DFP iniciais; a disponibilidade é confirmada na consulta oficial."""
    return (2023, 2024, 2025)


def fetch_company_financial_statements(
    service: CvmService, company: CompanyData, exercise: int
) -> CvmFinancialData:
    return service.load_financial_data(company, exercise)
