# Analisador Financeiro — Etapa 9

Aplicação Streamlit que consulta dados financeiros brutos de companhias abertas diretamente nos arquivos estruturados oficiais da Comissão de Valores Mobiliários (CVM).

## Escopo desta etapa

- Lista companhias a partir do cadastro oficial e as identifica pelo **código CVM**, com CNPJ e situação cadastral quando disponíveis.
- Baixa o DFP oficial do exercício selecionado e mantém cópia local em `data/cvm_cache/` para não repetir downloads.
- Carrega exclusivamente as demonstrações **consolidadas** BPA, BPP e DRE.
- Mostra uma prévia das contas brutas, sem alterar nomes, agrupar contas ou calcular indicadores.
- Cria uma demonstração de **Ativo padronizado** separada dos registros originais da CVM.
- Registra o destino de toda conta CVM como `MAPPED`, `UNMAPPED` ou `IGNORED`.

O sistema oferece análise individual e comparação objetiva de 2 a 5 companhias, sem diagnóstico, recomendações, score, classificação de risco, previsão ou conclusão automática.

## Dados brutos e dados padronizados

Os dados brutos retornados pela CVM nunca são alterados. `services/standardization_service.py` produz uma nova estrutura a partir deles. O mapeamento usa códigos da conta CVM como critério principal e é explícito em `ASSET_MAPPING_RULES`.

O modelo implementado para o Ativo preserva esta hierarquia:

```text
TOTAL ATIVO
├── ATIVO CIRCULANTE
│   ├── FINANCEIRO: Disponível; Aplicações de Liquidez e TVM
│   └── OPERACIONAL: Contas a receber; Estoques; Outros ativos circulantes
└── ATIVO NÃO CIRCULANTE
    ├── Realizável a L.P. Contas a Receber
    ├── Realizável a L.P. Estoques
    ├── Demais Realizáveis a Longo Prazo
    ├── Investimentos
    ├── Imobilizado
    └── Intangível
```

Contas de subtotal ou detalhamento que já estejam incluídas em uma conta mapeada recebem `IGNORED`, com motivo explícito, para evitar dupla contagem. Contas sem regra segura recebem `UNMAPPED` e aparecem na auditoria; elas nunca são descartadas silenciosamente.

### Passivo + Patrimônio Líquido

O modelo inclui Passivo Circulante (Fornecedores, Outras Obrigações e Empréstimos e Financiamentos), Passivo Não Circulante (Empréstimos e Financiamentos e Outras Obrigações), Total Capital de Terceiros e Patrimônio Líquido (Capital, Reservas de Capital; Reservas de lucros; Ajustes de Avaliação Patrimonial). O Total Capital de Terceiros é calculado como soma dos passivos circulante e não circulante.

### DRE

A DRE segue exatamente a ordem do professor. Receita, custos e despesas são linhas de origem (`SOURCE`) mapeadas da CVM; linhas com `(=)`, como Lucro Bruto e Resultado Líquido do Período, são subtotais calculados (`CALCULATED`). Os sinais econômicos publicados pela CVM são preservados para que os subtotais conciliem com o resultado oficial. Valores não recorrentes só são preenchidos se houver regra explícita — atualmente permanecem em zero, sem inferência automática.

As contas sem regra explícita ficam `UNMAPPED`; subtotais e detalhamentos já contidos em uma linha fonte ficam `IGNORED`, sempre com motivo na auditoria. A interface também compara os totais padronizados com os totais da CVM.

## VA, AV e AH

Após a padronização, `services/analysis_service.py` cria uma camada analítica independente. VA é o valor absoluto da categoria no exercício. AV é calculada como `linha / base × 100`: a base é **TOTAL ATIVO** para BPA, **TOTAL PASSIVO + PL** para BPP e **RECEITA LÍQUIDA** para a DRE.

AH compara sempre exercícios consecutivos: `(valor atual / valor anterior - 1) × 100`. Além do percentual, o sistema preserva a variação absoluta (`atual - anterior`). Quando a base anterior é zero, AH é exibida como `n/a — base zero`; quando há troca de sinal, como `mudança de sinal`. A tolerância para tratar um valor como zero é `1e-9`.

AV e AH alcançam contas, categorias agregadas e subtotais calculados. A interface usa blocos por exercício no formato VA / AV / AH, deixando AH ausente no exercício mais antigo. Indicadores, gráficos e PDF não fazem parte desta etapa.

## Indicadores financeiros

Os indicadores seguem exclusivamente as fórmulas do professor e usam as categorias já padronizadas: IPL `(AP / PL) × 100`; PCT `[(PC + PNC) / PL] × 100`; CE `[PC / (PC + PNC)] × 100`; EFSAT `(PF / AT) × 100`; LG `(AC + RLP) / (PC + PNC)`; LC `AC / PC`; LS `(DISP + DRL) / PC`; ICJ `LAJIR / DF`; GA `VL / ATm`; RSV `(LL / VL) × 100`; ROA `(LL / ATm) × 100`; e ROE `(LL / PLma) × 100`.

AP é Investimentos + Imobilizado + Intangível; PF soma os empréstimos e financiamentos de curto e longo prazo; RLP soma exclusivamente os realizáveis de longo prazo; DISP é Disponível + Aplicações de Liquidez e TVM; DRL é Contas a receber. Para GA e ROA, `ATm = (AT final + AT inicial) / 2`. Para ROE, `PLma = (PL inicial + PL final - LL) / 2`.

O exercício anterior é carregado internamente para calcular as médias do primeiro ano exibido, sem virar uma quarta coluna. Se um denominador for zero, o resultado é `N/A — denominador igual a zero`; nenhum sinal é convertido automaticamente. A interface mostra fórmula, numerador, denominador e status para auditoria.

## Variações e evolução

O sistema apresenta informações objetivas sobre a evolução dos dados. Não realiza interpretação financeira ou diagnóstico. Para cada conta e indicador, ele mostra variação absoluta (`atual - anterior`), variação relativa entre exercícios consecutivos, maior e menor exercício e tendência matemática: `crescimento contínuo`, `redução contínua`, `oscilação` ou `estável`.

Indicadores percentuais também exibem, separadamente, a diferença em pontos percentuais. Por exemplo, uma mudança de 1,20% para 0,54% é `-0,66 p.p.` e não “-55 pontos percentuais”. Base anterior zero aparece como `Novo valor` ou `Estável`, sem percentual; mudança de sinal recebe esse status e mantém a variação absoluta. A seção “Principais variações” ordena apenas a magnitude quantitativa — não indica importância, causa ou qualidade financeira.

## Gráficos

Os gráficos são descritivos e usam somente resultados existentes. As demonstrações incluem linhas para estrutura patrimonial e DRE, composição por AV e variações AH; valores monetários são exibidos em R$ milhões apenas na apresentação. Os indicadores são separados em gráficos de percentuais e de índices, sem conversão de unidade. Valores negativos permanecem abaixo de zero e valores ausentes não são convertidos em zero. Não há diagnóstico automático, recomendação ou previsão.

## Exportação

A aplicação exporta PDF e cinco CSVs (`ativo`, `passivo_pl`, `dre`, `indicadores` e `variacoes`), além de um ZIP com todos os CSVs. O PDF usa ReportLab e reúne identificação da companhia, exercícios, Ativo, Passivo + PL, DRE, indicadores, variações/evolução e gráficos. Os CSVs mantêm VA, AV, AH, valores negativos, status de base zero e mudança de sinal quando aplicáveis. Os arquivos baixados usam nome de companhia normalizado em ASCII.

## QA multiempresa

A validação de qualidade foi repetida com os DFPs consolidados oficiais de Magazine Luiza, Petrobras, Vale e Lojas Renner para 2023–2025, usando 2022 somente como base interna quando necessário. O registro objetivo de integração, reconciliações, mapeamentos, indicadores, gráficos e exportação está em `tests/QA_STAGE_8_1.md`.

## Comparação entre empresas

A seção **Comparação entre empresas** seleciona de 2 a 5 companhias diretamente do cadastro oficial da CVM e reúne somente os resultados que cada companhia já calculou individualmente. Ela exibe valores absolutos, os 12 indicadores, AV/AH, diferenças objetivas e gráficos de Receita Líquida, Resultado Líquido, PL, Capital de Terceiros, ROA, ROE, PCT e LC. Também disponibiliza CSV e PDF da comparação. Dados ausentes permanecem como `n/a`; base zero e mudança de sinal não são convertidas em percentuais artificiais.

### Como adicionar um mapeamento

Adicione uma `MappingRule` a `ASSET_MAPPING_RULES`, com o tipo da demonstração, o código CVM exato e uma categoria já existente no modelo. Em seguida, inclua um teste que cubra a nova regra e confirme a validação do total. Não crie uma categoria nova sem o modelo oficial do professor.

## Fonte oficial

- [Cadastro de companhias abertas](https://dados.cvm.gov.br/dataset/cia_aberta-cad)
- [DFP — Demonstrações Financeiras Padronizadas](https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp)
- [Diretório dos arquivos DFP](https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/)

Não há scraping do site visual da CVM e não há valores fictícios. Se um arquivo ou demonstração não estiver disponível, a aplicação informa o erro.

## Regra para reapresentações

Para cada companhia, exercício e demonstração, a aplicação usa somente as linhas com a maior `VERSAO` numérica fornecida pela CVM. Se a coluna de versão estiver inválida ou ambígua, a consulta é interrompida em vez de escolher registros silenciosamente. A prévia informa a versão usada.

## Como executar localmente

Pré-requisito: Python 3.10 ou superior instalado.

```bash
pip install -r requirements.txt
streamlit run app.py
```

O navegador abrirá a aplicação automaticamente. Se isso não ocorrer, use o endereço local indicado pelo Streamlit no terminal.

## Publicação pública

Para a arquitetura atual, a alternativa mais simples é **Streamlit Community Cloud**: ela executa o `app.py` diretamente a partir de um repositório Git, instala as dependências de `requirements.txt` e fornece um endereço web sem exigir instalação do usuário final. O projeto inclui `.streamlit/config.toml` e não requer variáveis de ambiente, tokens ou segredos.

Para publicar, envie o repositório a um provedor Git e crie uma aplicação no Streamlit Community Cloud apontando para `app.py`. A plataforma instalará as dependências e executará o serviço. O cache `data/cvm_cache/` é local ao ambiente de execução e pode ser refeito com os dados públicos da CVM.

Os resultados são informações e cálculos objetivos derivados das demonstrações financeiras públicas. A aplicação não substitui análise profissional nem fornece recomendação de investimento.

## Estrutura

```text
financial-analyzer/
├── app.py
├── requirements.txt
├── README.md
├── services/
│   ├── cvm_service.py
│   ├── data_service.py
│   ├── standardization_service.py
│   ├── analysis_service.py
│   ├── visualization_service.py
│   ├── export_service.py
│   └── report_service.py
├── models/
│   └── financial_models.py
├── data/
├── assets/
└── tests/
    ├── test_cvm_service.py
    ├── test_standardization_service.py
    └── test_export_service.py
```

## Testes

Os testes unitários não acessam a internet: usam um ZIP em memória com o mesmo layout de arquivo da CVM para validar identificação da companhia, filtro de exercício e empresa, BPA/BPP/DRE, seleção da maior versão e cache. A suíte de padronização cobre mapeamento conhecido, conta desconhecida, preservação do original, auditoria, totais, validação, contas adicionais e versionamento.

```bash
python -m unittest discover -s tests -v
```

## Próximas etapas

| Necessidade | Local previsto |
| --- | --- |
| Consulta à CVM, identificação da empresa e demonstrações brutas | `services/cvm_service.py` |
| Modelo oficial de Passivo/PL e DRE | `services/standardization_service.py` |
| Análises vertical/horizontal, indicadores e evolução | `services/analysis_service.py` |
| PDF, CSVs e ZIP | `services/export_service.py` |
| Evolução das entidades de empresa, período e demonstrações | `models/financial_models.py` |

`app.py` concentra a interface, consulta os dados e orquestra as camadas de análise, gráficos e exportação.
