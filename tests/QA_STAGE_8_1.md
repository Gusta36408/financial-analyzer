# Etapa 8.1 — QA Multiempresa

## Empresas testadas

- Magazine Luiza — CVM 22470 — CNPJ 47.960.950/0001-21
- Petróleo Brasileiro S.A. - Petrobras — CVM 9512 — CNPJ 33.000.167/0001-01
- Vale S.A. — CVM 4170 — CNPJ 33.592.510/0001-54
- Lojas Renner S.A. — CVM 8133 — CNPJ 92.754.738/0001-62

## Integração CVM

| Empresa | Exercícios validados | BPA / BPP / DRE | Versões CVM (2023 / 2024 / 2025) | Status |
| --- | --- | --- | --- | --- |
| Magazine Luiza | 2023–2025; 2022 como base interna | Encontradas, consolidadas | 1 / 1 / 1 | OK |
| Petrobras | 2023–2025; 2022 como base interna | Encontradas, consolidadas | 2 / 1 / 1 | OK |
| Vale | 2023–2025; 2022 como base interna | Encontradas, consolidadas | 1 / 3 / 2 | OK |
| Lojas Renner | 2023–2025; 2022 como base interna | Encontradas, consolidadas | 1 / 1 / 2 | OK |

As versões são a maior `VERSAO` numérica disponível no DFP oficial para a companhia, demonstração e exercício. Nenhuma versão foi escolhida arbitrariamente.

## Auditoria

| Empresa | Exercício | Diferença Ativo | Diferença Passivo + PL | Diferença DRE | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| Todas as quatro empresas | 2023 | R$ 0,00 | R$ 0,00 | R$ 0,00 | OK |
| Todas as quatro empresas | 2024 | R$ 0,00 | R$ 0,00 | R$ 0,00 | OK |
| Todas as quatro empresas | 2025 | R$ 0,00 | R$ 0,00 | R$ 0,00 | OK |

Foi conferido que as árvores padronizadas fecham com os totais CVM e que o resultado líquido calculado reconcilia com a DRE. VA, AV, AH, os 12 indicadores, evolução objetiva e gráficos foram exercitados com os mesmos objetos padronizados; 2022 permanece apenas como base interna dos indicadores de 2023.

## Mapeamento

| Empresa | UNMAPPED por exercício | IGNORED por exercício | Ocorrências relevantes |
| --- | --- | --- | --- |
| Magazine Luiza | 7 | 145 | Detalhes de atribuição do resultado e lucro por ação; não pertencem a categoria adicional do modelo. |
| Petrobras | 9 | 154–157 | Detalhes de atribuição do resultado e lucro por ação; não pertencem a categoria adicional do modelo. |
| Vale | 9 | 159–162 | Detalhes de atribuição do resultado e lucro por ação; não pertencem a categoria adicional do modelo. |
| Lojas Renner | 7 | 156–158 | Detalhes de atribuição do resultado e lucro por ação; não pertencem a categoria adicional do modelo. |

Correções realizadas: as regras CVM `2.03.05` (Lucros/Prejuízos Acumulados) e `2.03.09` (Participação dos Acionistas Não Controladores) passaram a compor o Patrimônio Líquido por caminhos existentes. A primeira entra em `Reservas de lucros`; a segunda entra diretamente em `Patrimônio Líquido`, sem forçar uma subcategoria indevida. A correção eliminou a diferença de R$ 1.899.000 identificada em Petrobras 2023.

## Indicadores

Os 12 indicadores (IPL, PCT, CE, EFSAT, LG, LC, LS, ICJ, GA, RSV, ROA e ROE) foram calculados para 2023–2025 nas quatro empresas, mantendo fórmula, unidade, numerador, denominador, status e a metodologia de PL médio já implementada para ROE. Não houve denominador zero neste conjunto. Indicadores percentuais preservam diferença em pontos percentuais; índices não foram convertidos em percentuais.

## Visualização

As séries patrimoniais, DRE, AV, AH, indicadores percentuais e indicadores em índice foram geradas para todas as empresas sem erro. Valores negativos, ausências, base zero e mudança de sinal foram preservados pelas camadas existentes.

## Exportação

Para cada empresa foram gerados PDF, `ativo.csv`, `passivo_pl.csv`, `dre.csv`, `indicadores.csv`, `variacoes.csv` e ZIP. Os ZIPs contêm exatamente os cinco CSVs. Os nomes de diretório e arquivo são normalizados em ASCII. A exportação consome os objetos calculados, sem fórmulas paralelas.

## Testes

35/35 testes unitários aprovados após as correções. A auditoria multiempresa reproduzível está em `work/qa_stage_8_1.py` e usa os DFPs oficiais cacheados.

## Problemas encontrados

- Crítico: nenhum.
- Importante: uma falha de mapeamento do Patrimônio Líquido em Petrobras, corrigida por códigos CVM explícitos `2.03.05` e `2.03.09`.
- Cosmético: nenhum.

## Conclusão

**APROVADA.** Nenhum diagnóstico, recomendação, ranking, comparação entre empresas ou funcionalidade da Etapa 9 foi introduzido.
