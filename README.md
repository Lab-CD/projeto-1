# 🏀 Quadra em Dados

Relatório interativo do Projeto 1 de Laboratório de Ciência de Dados, desenvolvido em **Python e Flask**. A análise compara Chicago Bulls e Minnesota Timberwolves nas partidas disponíveis na base. Resultados, gráficos, métodos e interpretação estão no próprio sistema web.

## 🚀 Executar localmente

No **PowerShell**, na raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Abra **http://127.0.0.1:5000**. Depois da primeira instalação, basta repetir o último comando.

Em Linux ou macOS, use `python3 -m venv .venv` e substitua `.\.venv\Scripts\python.exe` por `.venv/bin/python`.

### 🔄 Desenvolvimento

Para recarregar o servidor quando o código ou o CSV mudar:

```powershell
.\.venv\Scripts\python.exe main.py --dev
```

Templates HTML são recarregados automaticamente. Para ver mudanças no CSS, atualize a página no navegador.

## 🧭 Explorar o relatório

Use os filtros de equipe, variável, método ou medida e clique em **Atualizar análise**. As escolhas ficam registradas na URL.

| Página | Conteúdo |
|---|---|
| `/` | Visão geral das equipes |
| `/dicionario` | Significado, tipo, domínio e unidade das 28 colunas |
| `/preparacao` | Recorte, renomeação e conversão dos dados |
| `/qualidade` | Ausências, inconsistências e detectores de outliers |
| `/descritiva` | Medidas, boxplot, histograma com KDE e jogos extremos |
| `/comparacao` | Gráficos de barras, CV, IQR e assimetria |
| `/relatorio` | Análise completa, interpretação, métodos e conclusões |

A página **Relatório completo** reúne as explicações e a interpretação dos resultados. Os caminhos antigos `/sintese` e `/metodologia` redirecionam para suas seções nessa página.

## 📊 Base e método

- **Arquivo:** `data/raw/stats_times_regular_final.csv`, preservado sem alterações.
- **Origem:** 2.238 registros, 28 colunas e 30 equipes.
- **Recorte:** 148 registros, sendo 74 por equipe, de 22/10/2025 a 28/03/2026. São 146 partidas distintas; os dois confrontos diretos aparecem uma vez para cada equipe.
- **Unidade de análise:** uma equipe em uma partida. Jogos contra outros adversários entram nas estatísticas dos dois times, mas os dados desses adversários não entram nas médias nem nas referências comparativas.
- **Convenções:** desvio padrão amostral (`ddof=1`), quartis por interpolação linear, extremos pela regra de 1,5 × IQR e assimetria ajustada de Fisher–Pearson.
- **Tratamento:** zeros e extremos válidos são mantidos. Não há imputação automática. Os mecanismos de ausência são discutidos no relatório, sem execução de testes, pois não há valores ausentes no recorte atual.

A fonte original, a data de coleta e a licença do CSV não foram informadas. O sistema mostra o tamanho e o hash SHA-256 do arquivo para identificar a versão analisada.

## 🧩 Estrutura do projeto

| Caminho | Função |
|---|---|
| `analytics/` | Preparação, qualidade, estatísticas, detectores e gráficos |
| `app/` | Rotas Flask, apresentação, templates e estilos |
| `config.py` | Equipes, caminho do CSV e parâmetros da análise |
| `main.py` | Aplicação WSGI e execução local |
| `tests/` | Testes dos dados, cálculos, rotas e inicialização |

Os textos do relatório ficam em `app/templates/report/partials/`. Ao substituir o CSV, confira o esquema em `analytics/schema.py` e atualize os testes que verificam as 74 partidas por equipe.

## ✅ Testar

Com as dependências instaladas:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
