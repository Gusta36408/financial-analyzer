"""Integração com os arquivos estruturados oficiais da CVM.

Esta camada trabalha exclusivamente com dados brutos. Não padroniza contas e não
calcula indicadores. Os arquivos DFP consolidados (sufixo ``_con_``) são usados
para evitar a mistura entre demonstrações individuais e consolidadas.
"""

from __future__ import annotations

import logging
import os
import re
import zipfile
from pathlib import Path

import pandas as pd
import requests

from models.financial_models import (
    CompanyData,
    CvmFinancialData,
    FinancialAccount,
    RawFinancialStatement,
)


LOGGER = logging.getLogger(__name__)
BASE_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA"
CADASTRO_URL = f"{BASE_URL}/CAD/DADOS/cad_cia_aberta.csv"
DFP_URL_TEMPLATE = f"{BASE_URL}/DOC/DFP/DADOS/dfp_cia_aberta_{{year}}.zip"
REQUIRED_STATEMENTS = ("BPA", "BPP", "DRE")


class CvmServiceError(Exception):
    """Erro compreensível que pode ser mostrado na interface."""


class CvmDataNotFoundError(CvmServiceError):
    """Não há dado oficial para a combinação solicitada."""


class CvmDataAmbiguityError(CvmServiceError):
    """Há mais de uma versão possível sem regra segura para a escolha."""


class CvmService:
    """Baixa, mantém em cache e filtra os arquivos oficiais da CVM."""

    def __init__(self, cache_dir: Path | str | None = None, session: requests.Session | None = None) -> None:
        self.cache_dir = Path(cache_dir or Path("data") / "cvm_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = session or requests.Session()

    def list_companies(self) -> list[CompanyData]:
        """Lista companhias a partir do cadastro oficial, ordenadas por nome."""
        path = self._cached_download(CADASTRO_URL, "cad_cia_aberta.csv")
        try:
            frame = pd.read_csv(path, sep=";", encoding="latin1", dtype=str, keep_default_na=False)
        except (OSError, UnicodeError, pd.errors.ParserError) as error:
            LOGGER.exception("Não foi possível ler o cadastro CVM")
            raise CvmServiceError("Não foi possível ler o cadastro oficial da CVM.") from error

        required = {"CD_CVM", "DENOM_SOCIAL"}
        if not required.issubset(frame.columns):
            raise CvmServiceError("O cadastro oficial da CVM está em um formato inesperado.")

        if "SIT" in frame.columns:
            active = frame["SIT"].str.upper().str.strip().eq("ATIVO")
            if active.any():
                frame = frame[active]

        companies = [
            CompanyData(
                company_name=row["DENOM_SOCIAL"].strip(),
                cvm_code=self._text(row["CD_CVM"]),
                cnpj=self._optional_text(row.get("CNPJ_CIA") or row.get("CNPJ")),
                registration_status=self._optional_text(row.get("SIT")),
            )
            for _, row in frame.iterrows()
            if self._text(row["CD_CVM"]) and self._text(row["DENOM_SOCIAL"])
        ]
        return sorted(companies, key=lambda company: company.company_name.casefold())

    def load_financial_data(self, company: CompanyData, exercise: int) -> CvmFinancialData:
        """Carrega BPA, BPP e DRE consolidados de uma companhia e exercício."""
        archive = self._cached_download(DFP_URL_TEMPLATE.format(year=exercise), f"dfp_cia_aberta_{exercise}.zip")
        try:
            with zipfile.ZipFile(archive) as zipped_file:
                statements = {
                    statement_type: self._load_statement(zipped_file, company, exercise, statement_type)
                    for statement_type in REQUIRED_STATEMENTS
                }
        except zipfile.BadZipFile as error:
            LOGGER.exception("Arquivo DFP corrompido: %s", archive)
            raise CvmServiceError("O arquivo recebido da CVM está corrompido ou incompleto.") from error

        return CvmFinancialData(company=company, exercise=exercise, statements=statements)

    def _cached_download(self, url: str, filename: str) -> Path:
        """Armazena cada base oficial por nome; pedidos repetidos não baixam de novo."""
        destination = self.cache_dir / filename
        if destination.exists() and destination.stat().st_size > 0:
            return destination

        temporary = destination.with_suffix(destination.suffix + ".part")
        try:
            with self.session.get(url, stream=True, timeout=(10, 120)) as response:
                response.raise_for_status()
                with temporary.open("wb") as output:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            output.write(chunk)
            os.replace(temporary, destination)
        except requests.RequestException as error:
            temporary.unlink(missing_ok=True)
            LOGGER.exception("Falha ao baixar arquivo CVM: %s", url)
            raise CvmServiceError("Não foi possível consultar a CVM agora. Verifique sua conexão e tente novamente.") from error
        except OSError as error:
            temporary.unlink(missing_ok=True)
            LOGGER.exception("Falha no cache local da CVM")
            raise CvmServiceError("Não foi possível salvar os dados oficiais no cache local.") from error
        return destination

    def _load_statement(
        self, zipped_file: zipfile.ZipFile, company: CompanyData, exercise: int, statement_type: str
    ) -> RawFinancialStatement:
        filename = self._find_consolidated_statement_file(zipped_file, statement_type, exercise)
        try:
            with zipped_file.open(filename) as source:
                frame = pd.read_csv(source, sep=";", encoding="latin1", dtype=str, keep_default_na=False)
        except (KeyError, UnicodeError, pd.errors.ParserError) as error:
            LOGGER.exception("Não foi possível ler %s", filename)
            raise CvmServiceError(f"A demonstração {statement_type} da CVM não pôde ser lida.") from error

        filtered = self._filter_company_and_exercise(frame, company.cvm_code, exercise, statement_type)
        accounts = tuple(self._to_account(row) for _, row in filtered.iterrows())
        return RawFinancialStatement(
            statement_type=statement_type,
            accounts=accounts,
            source_file=filename,
            version=self._optional_text(filtered.iloc[0].get("VERSAO")),
        )

    @staticmethod
    def _find_consolidated_statement_file(zipped_file: zipfile.ZipFile, statement_type: str, exercise: int) -> str:
        pattern = re.compile(rf"(?:^|/).*_{statement_type}_con_{exercise}\.csv$", re.IGNORECASE)
        candidates = [name for name in zipped_file.namelist() if pattern.search(name)]
        if len(candidates) != 1:
            raise CvmDataNotFoundError(
                f"A CVM não disponibilizou uma demonstração consolidada {statement_type} para {exercise}."
            )
        return candidates[0]

    def _filter_company_and_exercise(
        self, frame: pd.DataFrame, cvm_code: str, exercise: int, statement_type: str
    ) -> pd.DataFrame:
        required_columns = {"CD_CVM", "DT_REFER", "CD_CONTA", "DS_CONTA", "VL_CONTA"}
        if not required_columns.issubset(frame.columns):
            raise CvmServiceError(f"O arquivo {statement_type} da CVM possui formato inesperado.")

        # O cadastro pode trazer ``22470`` enquanto o DFP usa ``022470``.
        # A comparação numérica normalizada preserva o código como publicado em
        # cada origem, mas impede que zeros à esquerda ocultem a companhia.
        company_rows = frame[
            frame["CD_CVM"].map(self._normalize_cvm_code).eq(self._normalize_cvm_code(cvm_code))
        ].copy()
        reference_dates = pd.to_datetime(company_rows["DT_REFER"], errors="coerce")
        rows = company_rows[reference_dates.dt.year.eq(exercise)].copy()
        if rows.empty:
            raise CvmDataNotFoundError(f"Não há {statement_type} para esta companhia no exercício de {exercise}.")

        # Regra de reapresentação: dentro da companhia, exercício e demonstração,
        # escolhemos apenas a maior VERSAO numérica publicada pela CVM. Se a coluna
        # estiver ausente, inválida ou ambígua, a aplicação interrompe a consulta.
        if "VERSAO" in rows.columns:
            versions = pd.to_numeric(rows["VERSAO"], errors="coerce")
            if versions.isna().any():
                raise CvmDataAmbiguityError(
                    f"A CVM informou versões ambíguas para {statement_type}; nenhum dado foi escolhido automaticamente."
                )
            rows = rows[versions.eq(versions.max())].copy()

        if "DT_FIM_EXERC" in rows.columns:
            end_dates = pd.to_datetime(rows["DT_FIM_EXERC"], errors="coerce")
            requested_period = rows[end_dates.dt.year.eq(exercise)].copy()
            if not requested_period.empty:
                rows = requested_period

        if rows.empty:
            raise CvmDataNotFoundError(f"A CVM não possui contas de {statement_type} para o período solicitado.")
        return rows.sort_values("CD_CONTA", kind="stable")

    def _to_account(self, row: pd.Series) -> FinancialAccount:
        raw_fields = {column: self._optional_text(value) for column, value in row.items()}
        return FinancialAccount(
            account_code=self._text(row["CD_CONTA"]),
            account_description=self._text(row["DS_CONTA"]),
            value=self._parse_cvm_number(row["VL_CONTA"]),
            period=self._optional_text(row.get("DT_FIM_EXERC")),
            raw_fields=raw_fields,
        )

    @staticmethod
    def _parse_cvm_number(value: object) -> float | None:
        text = CvmService._optional_text(value)
        if not text:
            return None
        normalized = text.replace(".", "").replace(",", ".") if "," in text else text
        try:
            return float(normalized)
        except ValueError:
            return None

    @staticmethod
    def _text(value: object) -> str:
        return "" if value is None else str(value).strip()

    @staticmethod
    def _normalize_cvm_code(value: object) -> str:
        code = CvmService._text(value)
        return code.lstrip("0") or "0"

    @staticmethod
    def _optional_text(value: object) -> str | None:
        text = CvmService._text(value)
        return text or None
