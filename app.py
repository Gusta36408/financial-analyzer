"""Interface do Analisador Financeiro — Etapa 2: consulta oficial à CVM."""

import logging

import pandas as pd
import streamlit as st

from models.financial_models import CvmFinancialData, EvolutionComparison, FinancialIndicator, RawFinancialStatement, StandardizedFinancialData, StandardizedNode, VerticalHorizontalAnalysis
from services.analysis_service import analyze_vertical_horizontal, calculate_indicators, compare_evolution, principal_variations
from services.cvm_service import CvmService, CvmServiceError
from services.data_service import fetch_company_financial_statements, get_available_periods, get_companies
from services.standardization_service import UNMAPPED, standardize_statements
from services.visualization_service import AH_SERIES, AV_SERIES, INDEX_INDICATORS, MONETARY_SERIES, PERCENT_INDICATORS, analysis_chart_rows, indicator_chart_rows
from services.export_service import csv_exports, csv_zip, generate_pdf, safe_filename
from services.comparison_service import AV_AH_ACCOUNTS, CompanyComparisonInput, comparison_chart_rows, comparison_csv, comparison_rows, difference_rows, generate_comparison_pdf, indicator_rows


logging.basicConfig(level=logging.INFO)

st.set_page_config(page_title="Analisador Financeiro", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")


def apply_styles() -> None:
    st.markdown(
        """
        <style>
            .block-container { max-width: 1120px; padding-top: 3rem; padding-bottom: 3rem; }
            .hero { padding: 1.4rem 0 1.8rem; }
            .hero h1 { margin-bottom: .25rem; }
            .muted { color: #5f6b7a; }
            div.stButton > button { width: 100%; min-height: 3rem; font-weight: 600; }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=24 * 60 * 60, show_spinner=False)
def load_companies() -> list:
    """Mantém o cadastro em memória durante o dia; o serviço também usa cache em disco."""
    return get_companies(CvmService())


def preview_dataframe(statement: RawFinancialStatement) -> pd.DataFrame:
    """Monta somente uma visualização das contas brutas, sem qualquer cálculo."""
    return pd.DataFrame(
        [
            {
                "Código": account.account_code,
                "Conta": account.account_description,
                "Valor": account.value,
                "Período": account.period,
                "Unidade": account.raw_fields.get("ESCALA_MOEDA"),
            }
            for account in statement.accounts
        ]
    )


def standardized_rows(node: StandardizedNode, depth: int = 0) -> list[dict]:
    """Transforma a árvore padronizada em linhas somente para apresentação."""
    rows = [{"Categoria": f"{'　' * depth}{node.name}", "Valor": node.value}]
    for child in node.children:
        rows.extend(standardized_rows(child, depth + 1))
    return rows


def audit_dataframe(standardized_data: StandardizedFinancialData, statement_type: str) -> pd.DataFrame:
    statement = standardized_data.statements[statement_type]
    return pd.DataFrame(
        [
            {
                "Código CVM": entry.account_code,
                "Conta CVM": entry.account_description,
                "Valor": entry.value,
                "Categoria padronizada": " > ".join(entry.category_path or ()),
                "Status": entry.status,
                "Tipo": entry.line_type,
                "Motivo": entry.reason,
            }
            for entry in statement.audit_entries
            if entry.status == UNMAPPED
        ]
    )


def render_standardized_data(standardized_data: StandardizedFinancialData) -> None:
    st.divider()
    st.subheader("Dados padronizados")
    st.caption("Nova estrutura derivada dos dados CVM, mantendo os registros brutos inalterados.")

    names = {"BPA": "Balanço Patrimonial — Ativo", "BPP": "Balanço Patrimonial — Passivo + PL", "DRE": "Demonstração do Resultado"}
    tabs = st.tabs([names[key] for key in ("BPA", "BPP", "DRE")])
    for tab, statement_type in zip(tabs, ("BPA", "BPP", "DRE")):
        statement = standardized_data.statements[statement_type]
        with tab:
            st.dataframe(pd.DataFrame(standardized_rows(statement.root)), use_container_width=True, hide_index=True)
            if statement_type == "DRE":
                st.caption("Linhas com (=) são subtotais calculados a partir das linhas de origem; AV e AH não são exibidas.")
    asset_statement = standardized_data.statements["BPA"]
    validation = asset_statement.validation
    if validation and validation.cvm_total is not None:
        st.markdown("#### Validação do total do ativo")
        cvm_column, standardized_column, difference_column, status_column = st.columns(4)
        cvm_column.metric("Total CVM", validation.cvm_total)
        standardized_column.metric("Total padronizado", validation.standardized_total)
        difference_column.metric("Diferença", validation.difference)
        status_column.metric("Validação", "OK" if validation.is_within_tolerance else "Divergência")
        if not validation.is_within_tolerance:
            st.warning(f"Diferença percentual: {validation.difference_percent:.4f}%")

    liability_validation = standardized_data.statements["BPP"].validation
    if liability_validation:
        st.markdown("#### Validação do total do Passivo + PL")
        st.caption(f"CVM: {liability_validation.cvm_total} | Padronizado: {liability_validation.standardized_total} | Diferença: {liability_validation.difference}")

    st.markdown("#### Auditoria — Contas da CVM não mapeadas")
    selected_statement = st.selectbox("Demonstração para auditoria", options=["BPA", "BPP", "DRE"])
    table = audit_dataframe(standardized_data, selected_statement)
    if table.empty:
        st.success("Não há contas não mapeadas nesta demonstração.")
    else:
        st.dataframe(table, use_container_width=True, hide_index=True)


def render_analysis(analysis: VerticalHorizontalAnalysis) -> None:
    st.divider()
    st.subheader("Análise Vertical e Horizontal")
    names = {"BPA": "Ativo", "BPP": "Passivo + PL", "DRE": "Demonstração do Resultado"}
    for statement_type, title in names.items():
        st.markdown(f"#### {title}")
        statement_lines = [line for line in analysis.lines if line.statement_type == statement_type]
        categories = list(dict.fromkeys(line.category for line in statement_lines))
        lookup = {(line.category, line.exercise): line for line in statement_lines}
        rows = []
        for category in categories:
            row = {"Categoria": category}
            for year in reversed(analysis.exercises):
                line = lookup[(category, year)]
                row[f"{year} VA"] = line.va
                row[f"{year} AV (%)"] = line.av
                if year != analysis.exercises[0]:
                    row[f"{year} AH (%)"] = "n/a — base zero" if line.ah_status == "BASE_ZERO" else "mudança de sinal" if line.ah_status == "SIGN_CHANGE" else line.ah
                    row[f"{year} Variação absoluta"] = line.absolute_change
            rows.append(row)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_indicators(indicators: tuple[FinancialIndicator, ...], exercises: tuple[int, ...]) -> None:
    st.divider()
    st.subheader("Indicadores Financeiros")
    ordered_codes = ("IPL", "PCT", "CE", "EFSAT", "LG", "LC", "LS", "ICJ", "GA", "RSV", "ROA", "ROE")
    lookup = {(indicator.code, indicator.exercise): indicator for indicator in indicators}
    rows = []
    for code in ordered_codes:
        sample = lookup[(code, exercises[-1])]
        row = {"Indicador": code, "Descrição": sample.name}
        for year in reversed(exercises):
            indicator = lookup[(code, year)]
            row[str(year)] = "N/A" if indicator.value is None else indicator.value
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    for code in ordered_codes:
        with st.expander(f"Fórmula e auditoria: {code}"):
            for year in reversed(exercises):
                indicator = lookup[(code, year)]
                st.markdown(f"**{year} — {indicator.name}**: `{indicator.formula}`")
                st.caption(f"Numerador: {indicator.numerator} | Denominador: {indicator.denominator} | Status: {indicator.status}")


def render_evolution(comparisons: tuple[EvolutionComparison, ...], exercise: int) -> None:
    st.divider()
    st.subheader("Variações e evolução")
    st.caption("Informações objetivas sobre os valores; esta seção não apresenta diagnóstico ou interpretação financeira.")
    st.markdown(f"#### Principais variações — {exercise}")
    highlights = principal_variations(comparisons, exercise)
    for item in highlights:
        change = f"{item.percentage_point_change:+.2f} p.p." if item.percentage_point_change is not None else f"{item.relative_change:+.2f}%"
        st.markdown(f"- **{item.item}**: {item.classification} de {change}; variação absoluta: {item.absolute_change:+.2f}.")
    for statement_type, title in (("BPA", "Ativo"), ("BPP", "Passivo + PL"), ("DRE", "DRE"), ("INDICATOR", "Indicadores — evolução")):
        st.markdown(f"#### {title}")
        rows = [{"Item": item.item, "Atual": item.current_value, "Anterior": item.previous_value, "Variação absoluta": item.absolute_change, "Variação relativa (%)": item.relative_change, "p.p.": item.percentage_point_change, "Classificação": item.classification, "Evolução": item.trend, "Maior valor": item.maximum_exercise, "Menor valor": item.minimum_exercise} for item in comparisons if item.statement_type == statement_type and item.current_exercise == exercise]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_charts(analysis: VerticalHorizontalAnalysis, indicators: tuple[FinancialIndicator, ...]) -> None:
    st.divider()
    st.subheader("Gráficos — Demonstrações Financeiras")
    st.caption("Visualizações descritivas dos dados calculados; não representam diagnóstico financeiro.")
    for title, categories in MONETARY_SERIES.items():
        st.markdown(f"#### {title} — R$ milhões")
        frame = pd.DataFrame(analysis_chart_rows(analysis, categories)).set_index("Exercício") / 1_000_000
        st.line_chart(frame, use_container_width=True)
    st.markdown("#### Composição por Análise Vertical")
    tabs = st.tabs(list(AV_SERIES))
    for tab, (title, categories) in zip(tabs, AV_SERIES.items()):
        with tab:
            frame = pd.DataFrame(analysis_chart_rows(analysis, categories, "av")).set_index("Exercício")
            st.area_chart(frame, use_container_width=True)
    st.markdown("#### Análise Horizontal — variação percentual")
    ah = pd.DataFrame(analysis_chart_rows(analysis, AH_SERIES, "ah")).set_index("Exercício")
    st.line_chart(ah, use_container_width=True)
    st.subheader("Gráficos — Indicadores")
    percentage = pd.DataFrame(indicator_chart_rows(indicators, PERCENT_INDICATORS)).set_index("Exercício")
    index = pd.DataFrame(indicator_chart_rows(indicators, INDEX_INDICATORS)).set_index("Exercício")
    first, second = st.columns(2)
    with first:
        st.markdown("#### Percentuais (%)")
        st.line_chart(percentage, use_container_width=True)
    with second:
        st.markdown("#### Índices")
        st.line_chart(index, use_container_width=True)


def render_exports(raw: CvmFinancialData, analysis: VerticalHorizontalAnalysis, indicators: tuple[FinancialIndicator, ...], comparisons: tuple[EvolutionComparison, ...]) -> None:
    st.divider(); st.subheader("Exportar resultados")
    exports = csv_exports(analysis, indicators, comparisons)
    safe_name = safe_filename(raw.company.company_name)
    pdf = generate_pdf(raw, analysis, indicators, comparisons)
    st.download_button("Baixar PDF", pdf, f"analise_financeira_{safe_name}_{analysis.exercises[0]}_{analysis.exercises[-1]}.pdf", "application/pdf")
    columns = st.columns(3)
    for index, (name, content) in enumerate(exports.items()):
        columns[index % 3].download_button(f"Baixar {name}", content, name, "text/csv")
    st.download_button("Baixar dados completos (ZIP)", csv_zip(exports), f"analise_financeira_{safe_name}_dados.zip", "application/zip")


def build_comparison_input(service: CvmService, company, exercises: tuple[int, ...]) -> CompanyComparisonInput:
    raw = [fetch_company_financial_statements(service, company, year) for year in (exercises[0] - 1, *exercises)]
    standardized = [standardize_statements(item) for item in raw]
    analysis = analyze_vertical_horizontal(standardized[1:])
    indicators = calculate_indicators(standardized, exercises)
    return CompanyComparisonInput(company, analysis, indicators, compare_evolution(analysis, indicators))


def render_comparison(items: tuple[CompanyComparisonInput, ...]) -> None:
    st.divider(); st.subheader("Comparação entre empresas")
    st.caption("Tabelas e gráficos objetivos sobre resultados já calculados individualmente; sem ranking, diagnóstico ou recomendação.")
    values = pd.DataFrame(comparison_rows(items)); indicators = pd.DataFrame(indicator_rows(items))
    st.markdown("#### Valores absolutos"); st.dataframe(values, use_container_width=True, hide_index=True)
    st.markdown("#### Indicadores"); st.dataframe(indicators, use_container_width=True, hide_index=True)
    st.markdown("#### Estrutura e evolução (AV/AH)")
    st.dataframe(pd.DataFrame(comparison_rows(items, AV_AH_ACCOUNTS, "av")), use_container_width=True, hide_index=True)
    ah = pd.DataFrame(comparison_rows(items, AV_AH_ACCOUNTS, "ah")).replace({None: "n/a"})
    st.dataframe(ah, use_container_width=True, hide_index=True)
    last_year = items[0].analysis.exercises[-1]
    st.markdown(f"#### Diferenças objetivas — {last_year}")
    differences = difference_rows(items, "ROA", last_year, indicator=True) + difference_rows(items, "RECEITA LÍQUIDA", last_year)
    st.dataframe(pd.DataFrame(differences), use_container_width=True, hide_index=True)
    charts = (("Receita Líquida", "RECEITA LÍQUIDA", False), ("Resultado Líquido", "(=) RESULTADO LÍQUIDO DO PERÍODO", False), ("Patrimônio Líquido", "PATRIMÔNIO LÍQUIDO", False), ("Capital de Terceiros", "TOTAL CAPITAL DE TERCEIROS", False), ("ROA", "ROA", True), ("ROE", "ROE", True), ("PCT", "PCT", True), ("LC", "LC", True))
    st.markdown("#### Gráficos comparativos")
    for title, key, is_indicator in charts:
        st.markdown(f"**{title}**")
        frame = pd.DataFrame(comparison_chart_rows(items, key, is_indicator)).set_index("Exercício")
        if not is_indicator: frame = frame / 1_000_000
        st.line_chart(frame, use_container_width=True)
    safe = "_".join(safe_filename(item.company.company_name) for item in items)
    st.download_button("Baixar CSV da comparação", comparison_csv(items), f"comparacao_{safe}.csv", "text/csv")
    st.download_button("Baixar PDF da comparação", generate_comparison_pdf(items), f"comparacao_{safe}.pdf", "application/pdf")


def render_result(data: CvmFinancialData) -> None:
    st.divider()
    st.subheader("Dados brutos encontrados")
    st.success("Dados encontrados na CVM.")

    company_column, code_column, period_column = st.columns(3)
    company_column.metric("Empresa", data.company.company_name)
    code_column.metric("Código CVM", data.company.cvm_code)
    period_column.metric("Exercício", str(data.exercise))
    if data.company.cnpj:
        st.caption(f"CNPJ cadastral: {data.company.cnpj}")

    st.markdown("#### Demonstrações encontradas")
    names = {"BPA": "Balanço Patrimonial Ativo", "BPP": "Balanço Patrimonial Passivo", "DRE": "Demonstração de Resultado"}
    for statement_type in ("BPA", "BPP", "DRE"):
        statement = data.statements[statement_type]
        st.markdown(f"✓ {names[statement_type]}")
        with st.expander(f"Prévia: {names[statement_type]}", expanded=statement_type == "BPA"):
            st.caption(f"Arquivo oficial: {statement.source_file} | Versão CVM: {statement.version or 'não informada'}")
            st.dataframe(preview_dataframe(statement), use_container_width=True, hide_index=True)

    st.info("Esta tela mostra os dados brutos oficiais que dão origem às tabelas, gráficos e exportações abaixo.")


def main() -> None:
    apply_styles()
    st.markdown(
        """
        <div class="hero">
            <h1>📊 Analisador Financeiro</h1>
            <p class="muted">Análise simplificada das demonstrações financeiras de empresas brasileiras</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption("Fonte dos dados: Portal de Dados Abertos da CVM. As informações exibidas são consultadas nos arquivos oficiais.")
    try:
        with st.spinner("Carregando cadastro oficial de companhias da CVM..."):
            companies = load_companies()
    except CvmServiceError as error:
        st.error(str(error))
        st.stop()
    if not companies:
        st.error("A CVM não retornou companhias disponíveis no momento.")
        st.stop()

    company_options = {company.display_name: company for company in companies}

    left_column, right_column = st.columns(2, gap="large")
    with left_column:
        st.subheader("1. Seleção da empresa")
        selected_name = st.selectbox(
            "Companhia aberta",
            options=list(company_options),
            help="A busca usa o cadastro oficial da CVM e identifica a companhia pelo código CVM.",
        )

        st.subheader("2. Período")
        selected_period = st.selectbox(
            "Exercício da análise",
            options=get_available_periods(),
            index=2,
            help="A disponibilidade será confirmada no arquivo DFP oficial da CVM.",
        )

    with right_column:
        st.subheader("3. Tipo de análise")
        st.radio("Modalidade", options=["Análise individual"], index=0)
        st.caption("A consulta usa BPA, BPP e DRE consolidados da CVM.")

    st.subheader("4. Gerar análise")
    if st.button("Gerar análise", type="primary"):
        selected_company = company_options[selected_name]
        try:
            with st.spinner("Consultando os dados oficiais da CVM..."):
                years = [year for year in get_available_periods() if year <= selected_period]
                required_years = [years[0] - 1] + years
                raw_series = [fetch_company_financial_statements(CvmService(), selected_company, year) for year in required_years]
                data = raw_series[-1]
        except CvmServiceError as error:
            logging.exception("Falha na consulta CVM")
            st.error(str(error))
        else:
            st.session_state["cvm_data"] = data
            st.session_state["standardized_data"] = standardize_statements(data)
            standardized_series = [standardize_statements(item) for item in raw_series]
            st.session_state["analysis"] = analyze_vertical_horizontal(standardized_series[1:])
            st.session_state["indicators"] = calculate_indicators(standardized_series, tuple(years))
            st.session_state["evolution"] = compare_evolution(st.session_state["analysis"], st.session_state["indicators"])

    if data := st.session_state.get("cvm_data"):
        render_result(data)
    if standardized_data := st.session_state.get("standardized_data"):
        render_standardized_data(standardized_data)
    if analysis := st.session_state.get("analysis"):
        render_analysis(analysis)
    if indicators := st.session_state.get("indicators"):
        render_indicators(indicators, analysis.exercises)
    if evolution := st.session_state.get("evolution"):
        render_evolution(evolution, analysis.exercises[-1])
    if analysis := st.session_state.get("analysis"):
        render_charts(analysis, st.session_state["indicators"])
        render_exports(st.session_state["cvm_data"], analysis, st.session_state["indicators"], st.session_state["evolution"])

    st.divider(); st.subheader("Comparação entre empresas")
    selected_companies = st.multiselect("Companhias (2 a 5)", options=list(company_options), max_selections=5, key="comparison_companies")
    selected_exercises = tuple(st.multiselect("Exercícios em comum", options=list(get_available_periods()), default=list(get_available_periods()), key="comparison_exercises"))
    if st.button("Gerar comparação"):
        if len(selected_companies) < 2 or not selected_exercises:
            st.error("Selecione de 2 a 5 companhias e ao menos um exercício.")
        else:
            try:
                with st.spinner("Carregando dados oficiais e montando a comparação..."):
                    service = CvmService()
                    st.session_state["comparison"] = tuple(build_comparison_input(service, company_options[name], selected_exercises) for name in selected_companies)
            except (CvmServiceError, ValueError) as error:
                st.error(str(error))
    if items := st.session_state.get("comparison"):
        render_comparison(items)


if __name__ == "__main__":
    main()
