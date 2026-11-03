# Quadra em Dados

Relatório web em Python/Flask do Projeto 1 de Laboratório de Ciência de Dados.
Recorte: **Chicago Bulls e Minnesota Timberwolves**, em todas as partidas disponíveis.
O relatório, com resultados e interpretação crítica, está no próprio sistema.

## Instalar e executar

Validado com **Python 3.14.7 no Windows**. No PowerShell, na pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Abra **http://127.0.0.1:5000**. Encerre com `Ctrl+C`. Não é necessário ativar a venv.
Depois da instalação, basta repetir o último comando.

### Desenvolvimento com recarga automática

```powershell
.\.venv\Scripts\python.exe main.py --dev
```

- Python: o servidor reinicia automaticamente quando o código muda.
- HTML: os templates são recarregados sem reiniciar o servidor.
- CSS: o cache está desativado; atualize a página para ver a alteração.
- CSV: alterações reiniciam o servidor para recalcular as análises.

Não há atualização automática da aba do navegador. O modo `--dev` é para desenvolvimento local;
a execução padrão usa Waitress. O cálculo inicial dos detectores leva alguns segundos.

Em Linux/macOS, use `python3 -m venv .venv` e substitua o executável por `.venv/bin/python`.
Esse fluxo não foi validado nesta entrega. Gráficos e estilos funcionam sem CDN após instalar os requisitos.

## Navegação

Use os filtros e **Atualizar análise**; a seleção é preservada na URL.

| Endereço | Conteúdo |
|---|---|
| `/` | Visão geral e equipes |
| `/dicionario` | As 28 colunas, tipos, domínios e unidades |
| `/preparacao` | Recorte, conversões e seleção de colunas |
| `/qualidade` | Auditoria, missing e detectores de outliers |
| `/descritiva` | Medidas, boxplot, histograma/KDE e extremos |
| `/comparacao` | Barras, CV, IQR e assimetria |
| `/relatorio` | Relatório completo: tratamentos, métodos, análises das sete variáveis, gráficos e conclusões |

As telas de consulta apresentam os resultados interativos. Todas as explicações e interpretações
ficam na página **Relatório completo**, com navegação interna por seção. Os endereços antigos
`/sintese` e `/metodologia` redirecionam para essa página.

## Base e convenções

- CSV preservado em `data/raw/stats_times_regular_final.csv`.
- Origem: 2.238 registros, 28 colunas, 30 equipes. Recorte: **148 registros, 74 por equipe**,
  de **22/10/2025 a 28/03/2026**; 146 partidas distintas, incluindo dois confrontos diretos.
- Unidade: um time por partida. Equipes externas não entram em estatísticas ou referências.
- Fonte original, data de coleta e licença não informadas. Hash e tamanho são exibidos no sistema.
- Desvio amostral (`ddof=1`), quartis lineares, extremos por 1,5 × IQR e assimetria ajustada.
  Fórmulas e limitações completas estão no Relatório completo.
- Zeros e extremos válidos são preservados. Não há imputação automática.
  Os testes de mecanismos de ausência são discutidos, sem execução.

## Organização e manutenção

| Caminho | Responsabilidade |
|---|---|
| `analytics/` | Metadados, preparação, auditoria, estatística, detectores e gráficos; independente do Flask |
| `app/` | Rotas, contexto, formatação, templates e CSS |
| `config.py` | IDs das equipes, caminho da base e parâmetros |
| `main.py` | Ponto de entrada |
| `tests/` | Cálculos, dados, detectores, execução e integração web |

Edite explicações em `app/templates/report/partials/`, usadas exclusivamente no relatório,
e cálculos no módulo de `analytics/` correspondente.
Ao substituir a base, mantenha o esquema ou adapte `schema.py` e a preparação.
Os testes que conferem 74 jogos retratam a versão atual: revise-os ao atualizar o CSV.
O [plano de implementação](docs/PLANO_IMPLEMENTACAO.md) mapeia requisitos e pontos de extensão.

## Testar

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Também foram conferidos gráficos e filtros no Edge, em desktop e celular.
Ferramentas de inspeção e formatação não são requisitos de execução.
