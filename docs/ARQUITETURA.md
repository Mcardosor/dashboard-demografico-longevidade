# Arquitetura — Envelhecimento Populacional

Visão de ponta a ponta pra quem for rodar, estender ou dar manutenção neste projeto sem ajuda direta de quem construiu.

## Fluxo de dados

```
IBGE (Projeções de População 2010-2025)
        │
        │  (pipeline de tratamento NÃO está neste repositório —
        │   os .parquet em /data já vêm prontos pra uso)
        ▼
data/pop_ibge.parquet ──┐
data/ibge_municipios.parquet ├─► src/data.py::_carregar_base()
data/ibge_ufs.parquet ──┘        (junta os 3 parquets, normaliza sexo/idade)
        │
        ▼
src/data.py (carregar_dados, carregar_evolucao, anos_disponiveis)
        │  cache via @st.cache_data / @st.cache_resource
        ▼
src/charts.py::processar_dados() ──► deriva faixa etária + recorte 60+ por UF
        │
        ├─► src/mapa.py::deck()  (coroplético em pydeck, classes por quartil;
        │                         cortes de src/data.py::cortes_quartis())
        │
        ▼
app.py ──► monta sidebar/filtros, chama src/charts.py::fig_*() para cada gráfico,
           src/utils.py para HTML de KPIs/tabelas, src/themes.py para CSS e marca
        │
        ▼
Streamlit renderiza no navegador
```

**Limitação conhecida:** o pipeline que transforma os dados brutos do IBGE nos 3 `.parquet` de `data/` não está neste repositório. Pra atualizar os dados (ex: quando o IBGE lançar a projeção de 2026), é preciso reconstruir esse pipeline (fora do escopo deste repo) e substituir os arquivos em `data/`, mantendo o mesmo schema consumido por `_carregar_base()` (colunas: `cod_mun`, `ano`, `idade`, `sexo`, `populacao` em `pop_ibge.parquet`; ver `src/data.py` pros nomes exatos das outras duas tabelas).

## Módulos

| Arquivo | Responsabilidade |
|---|---|
| `app.py` | Entrada Streamlit — sidebar, filtros, layout, orquestra os módulos abaixo |
| `src/data.py` | Carregamento e cache dos Parquet (única camada que toca disco) |
| `src/charts.py` | Processamento (`processar_dados`) e as três figuras Plotly (rosca, pirâmide, linha) |
| `src/mapa.py` | O coroplético, em pydeck/deck.gl e sem basemap — ver [Performance](performance.md) |
| `src/utils.py` | Formatação de números, HTML de KPI cards/tabelas, layout comum dos gráficos |
| `src/themes.py` | Paleta light/dark, CSS global, wordmark da marca, toggle de tema e trava da roda do mouse |
| `scripts/preparar_geometria.py` | Build: simplifica a malha das UFs uma vez, para `data/ufs.geojson` |
| `scripts/medir_performance.py` | Mede tempo e payload de cada figura, sem o cache do Streamlit |
| `tests/` | 66 testes: malha, mapa, identidade visual e orçamento de tempo |

Não há camada de API nem banco de dados — tudo roda no processo do Streamlit, lendo Parquet do disco local.

## Ambiente e variáveis

Nenhuma variável de ambiente é necessária — não há credenciais, banco ou serviço externo. `.streamlit/config.toml` fixa `baseUrlPath = "cenarios/demografico-longevidade"` (precisa bater com a rota do proxy reverso em produção).

## Deploy

- **Imagem:** `docker-compose.yml` builda a imagem a partir do `Dockerfile` (Python 3.11-slim + Streamlit), com `COPY . .` — o código vai embutido na imagem, não em bind mount (só `data/` é bind-mounted, read-only).
- **Container:** `dashboard-demografico-longevidade`, **8508** no host para **8501** no container. A 8501 do host é do painel `demografico`, que segue no ar.
- **Produção (VM):** `/home/matheusrodrigues/dashboard-demografico-longevidade/`, exposto via nginx em `https://painel.cenarios.unb.br/cenarios/demografico-longevidade` (proxy_pass pra `localhost:8508`).

  O `location` do nginx é prefixo sem barra final, e `/cenarios/demografico` casaria também com `/cenarios/demografico-longevidade`. Quem resolve é a regra do prefixo mais longo, que faz a rota deste painel vencer — mas as duas precisam existir, e mexer numa exige testar a outra.
- **Rebuild após mudança de código:** como o código é `COPY`, uma alteração em `app.py`/`src/` exige `docker compose up -d --build` (bind mount não é suficiente pra pegar a mudança).

## Limitações conhecidas

- Pipeline de dados brutos (IBGE → Parquet) não versionado neste repo (ver seção Fluxo de dados acima).
- Cobertura de dados: 2010–2025, por UF (não há recorte municipal na visualização, embora `ibge_municipios.parquet` exista na base).
- **O tema escuro não recolore os gráficos.** O botão de tema apenas marca
  `data-theme="dark"` no `<html>` e injeta uma folha de CSS por cima; o
  `st.session_state.theme` nunca muda, então `THEMES["dark"]` não chega ao
  Python. O entorno escurece, mas mapa, rosca e pirâmide seguem com as cores
  do tema claro. Vem de antes deste painel e vale também para o
  `dashboard-demografico`.
- **O wordmark é reprodução.** A flor e o arranjo são fiéis; a tipografia do
  JPEG oficial não é reproduzível com fonte de sistema. O vetor do
  Observatório resolveria — ver [Identidade visual](identidade.md).

## Regerar o print do README

`docs/preview.png` envelhece calado — ninguém repara que ele mostra uma versão
antiga até alguém abrir o README. Com o painel rodando local:

```bash
chrome --headless=new --disable-gpu --hide-scrollbars   --window-size=1440,1100 --virtual-time-budget=45000   --screenshot=docs/preview.png   http://localhost:8508/cenarios/demografico-longevidade/
```

O `--virtual-time-budget` é o que importa: sem ele o print sai na tela de
carregamento, porque o Streamlit ainda está lendo os parquets.

## Testes

```bash
pytest                 # 66 testes
pytest -m "not tempo"  # o subconjunto que o CI roda
```

Os testes com a marca `tempo` cronometram relógio de parede e ficam fora do
CI: num runner compartilhado a medida diz mais sobre a carga da máquina alheia
do que sobre o código. O porquê está em `pytest.ini`.

O CI (`.github/workflows/ci.yml`) roda lint, testes e o build da imagem,
conferindo que o que ela instala é exatamente o lock.
