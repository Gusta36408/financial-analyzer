"""Testes unitários sem acesso à internet para a integração CVM."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from zipfile import ZIP_DEFLATED, ZipFile

from models.financial_models import CompanyData
from services.cvm_service import CADASTRO_URL, DFP_URL_TEMPLATE, CvmService


class FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int):
        yield self.content


class FakeSession:
    def __init__(self, responses: dict[str, bytes]) -> None:
        self.responses = responses
        self.calls: list[str] = []

    def get(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append(url)
        return FakeResponse(self.responses[url])


def make_dfp_archive(year: int) -> bytes:
    header = "CD_CVM;DT_REFER;VERSAO;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ESCALA_MOEDA\n"
    older_row = "012345;2024-12-31;1;2024-12-31;1;Conta antiga;10.00;MIL\n"
    latest_row = "012345;2024-12-31;2;2024-12-31;1;Conta oficial;20.00;MIL\n"
    other_company = "99999;2024-12-31;2;2024-12-31;1;Outra companhia;30.00;MIL\n"
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for statement_type in ("BPA", "BPP", "DRE"):
            archive.writestr(
                f"dfp_cia_aberta_{statement_type}_con_{year}.csv",
                header + older_row + latest_row + other_company,
            )
    return buffer.getvalue()


class CvmServiceTests(TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        year = 2024
        cadastro = (
            "CD_CVM;DENOM_SOCIAL;CNPJ_CIA;SIT\n"
            "12345;COMPANHIA DE TESTE S.A.;00.000.000/0001-00;ATIVO\n"
            "99999;COMPANHIA INATIVA S.A.;11.111.111/0001-11;CANCELADO\n"
        ).encode("latin1")
        self.session = FakeSession(
            {CADASTRO_URL: cadastro, DFP_URL_TEMPLATE.format(year=year): make_dfp_archive(year)}
        )
        self.service = CvmService(Path(self.temporary_directory.name), session=self.session)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_lists_active_company_from_official_cadastro_layout(self) -> None:
        companies = self.service.list_companies()
        self.assertEqual(len(companies), 1)
        self.assertEqual(companies[0].cvm_code, "12345")
        self.assertEqual(companies[0].cnpj, "00.000.000/0001-00")

    def test_loads_bpa_bpp_and_dre_for_correct_company_and_exercise(self) -> None:
        company = CompanyData("COMPANHIA DE TESTE S.A.", "12345")
        data = self.service.load_financial_data(company, 2024)
        self.assertEqual(set(data.statements), {"BPA", "BPP", "DRE"})
        for statement in data.statements.values():
            self.assertEqual(len(statement.accounts), 1)
            self.assertEqual(statement.accounts[0].account_description, "Conta oficial")
            self.assertEqual(statement.accounts[0].value, 20.0)
            self.assertEqual(statement.version, "2")

    def test_uses_disk_cache_for_repeated_archive_request(self) -> None:
        company = CompanyData("COMPANHIA DE TESTE S.A.", "12345")
        self.service.load_financial_data(company, 2024)
        self.service.load_financial_data(company, 2024)
        self.assertEqual(self.session.calls.count(DFP_URL_TEMPLATE.format(year=2024)), 1)
