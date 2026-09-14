"""Camada de VA, AV e AH sobre dados já padronizados."""

from models.financial_models import AnalysisLine, EvolutionComparison, FinancialIndicator, StandardizedFinancialData, StandardizedNode, VerticalHorizontalAnalysis


ZERO_TOLERANCE = 1e-9


def analyze_vertical_horizontal(data_by_exercise: list[StandardizedFinancialData]) -> VerticalHorizontalAnalysis:
    """Calcula AV e AH sem alterar os objetos padronizados de entrada."""
    ordered = sorted(data_by_exercise, key=lambda data: data.exercise)
    exercises = tuple(data.exercise for data in ordered)
    lines: list[AnalysisLine] = []
    for statement_type in ("BPA", "BPP", "DRE"):
        values_by_year = {data.exercise: _flatten(data.statements[statement_type].root) for data in ordered}
        categories = list(dict.fromkeys(category for values in values_by_year.values() for category in values))
        for category in categories:
            for index, year in enumerate(exercises):
                value = values_by_year[year].get(category, 0.0)
                base = _base_value(statement_type, values_by_year[year])
                av = value / base * 100 if abs(base) > ZERO_TOLERANCE else None
                if index == 0:
                    ah, absolute_change, status = None, None, "NO_PREVIOUS_PERIOD"
                else:
                    previous = values_by_year[exercises[index - 1]].get(category, 0.0)
                    absolute_change = value - previous
                    if abs(previous) <= ZERO_TOLERANCE:
                        ah, status = None, "BASE_ZERO"
                    elif previous * value < 0:
                        ah, status = None, "SIGN_CHANGE"
                    else:
                        ah, status = (value / previous - 1) * 100, "OK"
                lines.append(AnalysisLine(statement_type, category, year, value, av, ah, absolute_change, status))
    return VerticalHorizontalAnalysis(exercises, tuple(lines))


def _flatten(node: StandardizedNode) -> dict[str, float]:
    values = {node.name: node.value or 0.0}
    for child in node.children:
        values.update(_flatten(child))
    return values


def _base_value(statement_type: str, values: dict[str, float]) -> float:
    return values[{"BPA": "TOTAL ATIVO", "BPP": "TOTAL PASSIVO + PL", "DRE": "RECEITA LÍQUIDA"}[statement_type]]


def calculate_indicators(data_by_exercise: list[StandardizedFinancialData], display_exercises: tuple[int, ...]) -> tuple[FinancialIndicator, ...]:
    """Calcula exclusivamente os 12 indicadores definidos pelo professor."""
    series = {data.exercise: data for data in data_by_exercise}
    results: list[FinancialIndicator] = []
    for year in display_exercises:
        current, previous = series[year], series.get(year - 1)
        ac = _value(current, "BPA", "TOTAL ATIVO", "ATIVO CIRCULANTE")
        rlp = sum(_value(current, "BPA", "TOTAL ATIVO", "ATIVO NÃO CIRCULANTE", name) for name in ("Realizável a L.P. Contas a Receber", "Realizável a L.P. Estoques", "Demais Realizáveis a Longo Prazo"))
        at = _value(current, "BPA", "TOTAL ATIVO")
        ap = sum(_value(current, "BPA", "TOTAL ATIVO", "ATIVO NÃO CIRCULANTE", name) for name in ("Investimentos", "Imobilizado", "Intangível"))
        pc = _value(current, "BPP", "TOTAL PASSIVO + PL", "PASSIVO CIRCULANTE")
        pnc = _value(current, "BPP", "TOTAL PASSIVO + PL", "PASSIVO NÃO CIRCULANTE")
        pl = _value(current, "BPP", "TOTAL PASSIVO + PL", "PATRIMÔNIO LÍQUIDO")
        pf = _value(current, "BPP", "TOTAL PASSIVO + PL", "PASSIVO CIRCULANTE", "FINANCEIRO", "Empréstimos e Financiamentos") + _value(current, "BPP", "TOTAL PASSIVO + PL", "PASSIVO NÃO CIRCULANTE", "Empréstimos e Financiamentos")
        disp = _value(current, "BPA", "TOTAL ATIVO", "ATIVO CIRCULANTE", "FINANCEIRO", "Disponível") + _value(current, "BPA", "TOTAL ATIVO", "ATIVO CIRCULANTE", "FINANCEIRO", "Aplicações de Liquidez e TVM")
        drl = _value(current, "BPA", "TOTAL ATIVO", "ATIVO CIRCULANTE", "OPERACIONAL", "Contas a receber")
        lajir = _value(current, "DRE", "DRE", "(=) LUCRO OPERAC. I")
        df = _value(current, "DRE", "DRE", "(-) Despesas Financeiras")
        revenue = _value(current, "DRE", "DRE", "RECEITA LÍQUIDA")
        ll = _value(current, "DRE", "DRE", "(=) RESULTADO LÍQUIDO DO PERÍODO")
        results.extend((_ratio("IPL", "Imobilização do Patrimônio Líquido", year, ap, pl, True, "(AP / PL) × 100"), _ratio("PCT", "Participação de Capital de Terceiros", year, pc + pnc, pl, True, "[(PC + PNC) / PL] × 100"), _ratio("CE", "Composição do Endividamento", year, pc, pc + pnc, True, "[PC / (PC + PNC)] × 100"), _ratio("EFSAT", "Encargos Financeiros sobre o Ativo Total", year, pf, at, True, "(PF / AT) × 100"), _ratio("LG", "Liquidez Geral", year, ac + rlp, pc + pnc, False, "(AC + RLP) / (PC + PNC)"), _ratio("LC", "Liquidez Corrente", year, ac, pc, False, "AC / PC"), _ratio("LS", "Liquidez Seca", year, disp + drl, pc, False, "(DISP + DRL) / PC"), _ratio("ICJ", "Índice de Cobertura de Juros", year, lajir, df, False, "LAJIR / DF"), _ratio("RSV", "Rentabilidade sobre Vendas", year, ll, revenue, True, "(LL / VL) × 100")))
        if previous is None:
            results.extend(_not_available(code, name, year, unit, formula) for code, name, unit, formula in (("GA", "Giro do Ativo", "vezes", "VL / ATm"), ("ROA", "Rentabilidade sobre o Ativo", "%", "(LL / ATm) × 100"), ("ROE", "Rentabilidade sobre o Patrimônio Líquido", "%", "(LL / PLma) × 100")))
        else:
            atm = (at + _value(previous, "BPA", "TOTAL ATIVO")) / 2
            plma = ( _value(previous, "BPP", "TOTAL PASSIVO + PL", "PATRIMÔNIO LÍQUIDO") + pl - ll) / 2
            results.extend((_ratio("GA", "Giro do Ativo", year, revenue, atm, False, "VL / ATm"), _ratio("ROA", "Rentabilidade sobre o Ativo", year, ll, atm, True, "(LL / ATm) × 100"), _ratio("ROE", "Rentabilidade sobre o Patrimônio Líquido", year, ll, plma, True, "(LL / PLma) × 100")))
    return tuple(results)


def _value(data: StandardizedFinancialData, statement: str, *path: str) -> float:
    node = data.statements[statement].root
    for expected in path:
        if node.name == expected: continue
        node = next(child for child in node.children if child.name == expected)
    return node.value or 0.0


def _ratio(code: str, name: str, year: int, numerator: float, denominator: float, percent: bool, formula: str) -> FinancialIndicator:
    if abs(denominator) <= ZERO_TOLERANCE: return _not_available(code, name, year, "%" if percent else "vezes", formula, numerator, denominator)
    return FinancialIndicator(code, name, year, numerator / denominator * (100 if percent else 1), "%" if percent else "vezes", numerator, denominator, formula, "OK")


def _not_available(code: str, name: str, year: int, unit: str, formula: str, numerator: float | None = None, denominator: float | None = None) -> FinancialIndicator:
    return FinancialIndicator(code, name, year, None, unit, numerator, denominator, formula, "N/A — denominador igual a zero")


def compare_evolution(analysis: VerticalHorizontalAnalysis, indicators: tuple[FinancialIndicator, ...]) -> tuple[EvolutionComparison, ...]:
    """Compara valores já calculados; não produz interpretação financeira."""
    series: dict[tuple[str, str], list[tuple[int, float, bool]]] = {}
    for line in analysis.lines:
        series.setdefault((line.statement_type, line.category), []).append((line.exercise, line.va, False))
    for indicator in indicators:
        if indicator.value is not None:
            series.setdefault(("INDICATOR", indicator.code), []).append((indicator.exercise, indicator.value, indicator.unit == "%"))
    comparisons = []
    for (statement_type, item), values in series.items():
        values.sort()
        trend = _trend([value for _, value, _ in values])
        maximum = max(values, key=lambda item: item[1])[0]; minimum = min(values, key=lambda item: item[1])[0]
        for index, (year, current, is_percent) in enumerate(values):
            if index == 0:
                comparisons.append(EvolutionComparison(item, statement_type, year, None, current, None, None, None, None, "Sem período anterior", trend, maximum, minimum, "NO_PREVIOUS_PERIOD")); continue
            previous_year, previous, _ = values[index - 1]
            absolute = current - previous
            if abs(previous) <= ZERO_TOLERANCE:
                classification, relative, status = ("Estável", None, "BASE_ZERO") if abs(current) <= ZERO_TOLERANCE else ("Novo valor", None, "BASE_ZERO")
            elif previous * current < 0:
                classification, relative, status = "Mudança de sinal", None, "SIGN_CHANGE"
            elif abs(absolute) <= ZERO_TOLERANCE:
                classification, relative, status = "Estável", 0.0, "OK"
            elif absolute > 0:
                classification, relative, status = "Aumento", (current / previous - 1) * 100, "OK"
            else:
                classification, relative, status = "Redução", (current / previous - 1) * 100, "OK"
            comparisons.append(EvolutionComparison(item, statement_type, year, previous_year, current, previous, absolute, relative, absolute if is_percent else None, classification, trend, maximum, minimum, status))
    return tuple(comparisons)


def principal_variations(comparisons: tuple[EvolutionComparison, ...], exercise: int, limit: int = 5) -> tuple[EvolutionComparison, ...]:
    """Seleciona as maiores variações relativas quantitativas do exercício."""
    candidates = [item for item in comparisons if item.current_exercise == exercise and item.relative_change is not None]
    return tuple(sorted(candidates, key=lambda item: abs(item.relative_change or 0), reverse=True)[:limit])


def _trend(values: list[float]) -> str:
    if all(abs(value - values[0]) <= ZERO_TOLERANCE for value in values): return "estável"
    if all(left < right for left, right in zip(values, values[1:])): return "crescimento contínuo"
    if all(left > right for left, right in zip(values, values[1:])): return "redução contínua"
    return "oscilação"
