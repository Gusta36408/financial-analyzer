# Etapa 9 — Comparação e preparação de publicação

## Empresas e períodos

Magazine Luiza, Petrobras, Vale e Lojas Renner foram revalidadas para 2023–2025, com 2022 usado apenas como base interna. A comparação das quatro empresas consumiu exatamente os resultados individuais já auditados.

## Comparação

- Comparação de 2, 3 e 4 empresas coberta por testes.
- Valores absolutos, 12 indicadores, AV, AH e diferenças objetivas cobertos.
- Percentuais usam pontos percentuais; índices e valores monetários mantêm diferença absoluta e relativa quando aplicável.
- Valores ausentes permanecem ausentes; base zero e mudança de sinal não recebem percentual artificial.
- Gráficos comparativos, CSV e PDF gerados a partir das mesmas estruturas calculadas.

## Regressão e exportação

As quatro empresas continuam com BPA, BPP e DRE conciliados. A exportação individual continua no fluxo anterior; a comparação gerou CSV e PDF válidos para quatro empresas.

## Preparação de deploy

- `requirements.txt` contém as dependências de execução.
- `app.py` é o entrypoint Streamlit.
- `.streamlit/config.toml` permite execução headless e desativa telemetria de uso.
- `.gitignore` exclui cache CVM, arquivos de trabalho e segredos opcionais.
- Não há caminhos absolutos, segredos ou credenciais no código de produção.
- A integração CVM usa cache local e timeout de conexão/leitura; falhas são apresentadas ao usuário como mensagens amigáveis.

## Limitações restantes

O deploy público não foi efetuado, pois requer a criação e autorização de uma conta/projeto no provedor escolhido. A disponibilidade e a velocidade de novas consultas dependem da CVM e do primeiro download de cada DFP no ambiente publicado.

## Status

**APROVADA.** Nenhum ranking, score, diagnóstico ou recomendação foi introduzido.
