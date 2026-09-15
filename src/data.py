import json
import os

import pandas as pd
import streamlit as st

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


@st.cache_resource(show_spinner=False)
def carregar_geojson() -> dict:
    """Carrega a malha das UFs usada no mapa coroplético.

    Lê `ufs.geojson`, que é a saída de `scripts/preparar_geometria.py`:
    simplificado topologicamente, com 5 casas decimais e só a propriedade
    `sigla`. O `brazil-states.geojson` cru continua no repositório como
    **origem** do pré-processamento — 3,4 MB e 85.585 vértices —, mas não é
    lido em execução. Ver docs/performance.md.

    Cacheado como recurso (`cache_resource`) porque o dicionário é
    compartilhado entre sessões e não deve ser copiado a cada rerun.

    Returns:
        dict: GeoJSON com a geometria dos estados, chaveado por
            `properties.sigla` (UF).
    """
    path = os.path.join(_DATA_DIR, "ufs.geojson")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


#: Último ano que o IBGE classifica como **estimativa** na revisão 2024. De
#: 2023 em diante é **projeção** — hipóteses de fecundidade, mortalidade e
#: migração, não contagem. O relatório metodológico (cap. 1) é explícito:
#: "estimativas (2000 a 2022) e projeções (2023 a 2070)".
#:
#: A fronteira importa porque o painel a mostra: linha tracejada na evolução,
#: "(projeção)" no seletor e no hero. Antes da troca de base o painel ia até
#: 2025 sem dizer que os três últimos anos já eram projetados.
ESTIMATIVA_ATE = 2022


def eh_projecao(ano: int) -> bool:
    """True para os anos que o IBGE projeta em vez de estimar."""
    return ano > ESTIMATIVA_ATE


@st.cache_data(show_spinner=False)
def _carregar_base() -> pd.DataFrame:
    """A base do painel: população por UF, ano, sexo e idade simples.

    Lê `pop_uf.parquet`, saída de `scripts/preparar_projecao.py` a partir da
    tab1 das Projeções da População do IBGE (revisão 2024). Cobre 2000-2070,
    27 UFs, idade 0 a **90** — e 90 é o balde aberto "90 ou mais".

    Já vem no grão que o painel usa; não há junção nenhuma a fazer. A base
    anterior era municipal (14,4 milhões de linhas, 23 MB) e todo gráfico a
    somava por UF antes de desenhar — o município era peso morto. Esta tem
    349 mil linhas e 0,9 MB para os mesmos números: conferido célula a célula
    em 2010-2025, 8 células de 69.984 divergem, no máximo 66 pessoas
    (arredondamento de município para UF). Ver docs/historico/levantamento-projecoes.md.

    Returns:
        pd.DataFrame: colunas `uf`, `ano`, `idade`, `sexo` ("M"/"F"),
            `populacao`.
    """
    pop = pd.read_parquet(os.path.join(_DATA_DIR, "pop_uf.parquet"))
    return pop.astype({"ano": "int64", "idade": "int64"})[
        ["uf", "ano", "idade", "sexo", "populacao"]
    ]


@st.cache_data(show_spinner=False)
def carregar_indicadores() -> pd.DataFrame:
    """Esperança de vida por UF e ano, ao nascer e aos 60, por sexo.

    Saída de `scripts/preparar_projecao.py` a partir da tab4 do IBGE. Os
    valores são os oficiais, não calculados aqui — a tábua de mortalidade
    (tab5) daria o mesmo número com 24 MB a mais.

    Returns:
        pd.DataFrame: colunas `uf`, `ano`, `e0_T`, `e0_H`, `e0_M`, `e60_T`,
            `e60_H`, `e60_M` (anos).
    """
    ind = pd.read_parquet(os.path.join(_DATA_DIR, "indicadores_uf.parquet"))
    return ind.astype({"ano": "int64"})


def esperanca_aos_60(ufs: list, ano: int) -> float:
    """Esperança de vida aos 60 anos, para um recorte de UFs.

    O IBGE publica o `e60` por UF e para o Brasil, não para um conjunto
    arbitrário de estados. Para o recorte, a média das UFs **ponderada pela
    população de 60+** de cada uma — que é a população a que o indicador se
    refere. Conferido contra o valor oficial do Brasil: 22,71 contra 22,73 em
    2025, e diferença abaixo de 0,01 ano em 2010, 2050 e 2070.

    Args:
        ufs: siglas das UFs do recorte.
        ano: ano de referência.

    Returns:
        float: anos de vida esperados aos 60; 0.0 num recorte vazio.
    """
    ind = carregar_indicadores()
    ind = ind[(ind["ano"] == ano) & ind["uf"].isin(ufs)].set_index("uf")["e60_T"]
    if ind.empty:
        return 0.0
    base = _carregar_base()
    peso = (
        base[(base["ano"] == ano) & (base["idade"] >= 60) & base["uf"].isin(ufs)]
        .groupby("uf")["populacao"].sum()
        .reindex(ind.index, fill_value=0)
    )
    if not peso.sum():
        return float(ind.mean())
    return float((ind * peso).sum() / peso.sum())


@st.cache_data(show_spinner=False)
def anos_disponiveis() -> list:
    """Lista os anos da base, do mais distante (2070) para o mais antigo (2000).

    Returns:
        list: anos (int) disponíveis na base, em ordem decrescente.
    """
    return sorted(_carregar_base()["ano"].unique().tolist(), reverse=True)


def ano_padrao() -> int:
    """O ano que o painel abre mostrando: o ano corrente.

    Não é o mais recente da base — esse é 2070, e abrir o painel em 2070
    apresentaria a hipótese mais distante como se fosse o retrato de hoje.
    Também não é o último ano estimado (2022): velho demais para um painel
    que se propõe atual. O ano corrente é projeção, e o painel diz isso.

    Returns:
        int: o ano corrente, limitado ao intervalo da base.
    """
    from datetime import date
    anos = anos_disponiveis()
    return min(max(date.today().year, anos[-1]), anos[0])


@st.cache_data(show_spinner="Carregando dados populacionais…")
def carregar_dados(ano: int) -> pd.DataFrame:
    """Agrega a população de um ano específico por UF, idade e sexo.

    Args:
        ano: ano de referência (ex: 2024) presente em `anos_disponiveis()`.

    Returns:
        pd.DataFrame: colunas `uf`, `idade`, `sexo`, `populacao` (uma linha
            por UF/idade/sexo).
    """
    df = _carregar_base()
    return (
        df[df["ano"] == ano]
        .groupby(["uf", "idade", "sexo"], as_index=False)["populacao"]
        .sum()
    )


@st.cache_resource(show_spinner=False)
def carregar_evolucao() -> pd.DataFrame:
    """Agrega a população total por UF em cada ano, para o gráfico de evolução.

    Cacheado como recurso porque é usado só para a série histórica (não
    varia por filtro de ano) e evita reprocessar a base inteira a cada aba.

    Returns:
        pd.DataFrame: colunas `uf`, `ano`, `populacao`.
    """
    return _carregar_base().groupby(["uf", "ano"], as_index=False)["populacao"].sum()


@st.cache_data(show_spinner=False)
def cortes_quartis() -> tuple[float, float, float]:
    """Os três cortes que dividem as UFs em quartis no mapa.

    Calculados **uma vez, sobre todos os anos (2000-2070) e todas as UFs
    juntos** — não por ano e não sobre o filtro. Os dois motivos são de
    leitura, não de implementação:

    - **Por ano não serve.** Quartil é medida relativa: recalculado a cada
      ano, ele sempre põe um quarto das UFs em cada classe. O mapa de 2010 e
      o de 2050 sairiam iguais, e o envelhecimento do país — que é o assunto
      do painel — ficaria invisível. Com corte fixo o mapa escurece década a
      década: 2000 inteiro na classe mais clara, 2070 inteiro na mais escura.
    - **Sobre o filtro, muito menos.** Recalcular sobre os estados
      selecionados faria os sobreviventes trocarem de cor a cada filtro. A
      cor precisa seguir o estado, não a posição dele num recorte.

    O custo assumido: a proporção de 60+ vai de 4% a 40% no período, e
    quatro cortes que cubram tudo isso separam pouco dentro de um ano só.
    Em 2025, 22 das 27 UFs caem na segunda classe. Os cortes anteriores,
    sobre 2010-2025, separavam 2025 melhor (2/3/4/18) — e pintavam 2040 em
    diante inteiro na classe mais escura. Decisão de 15/set/2026, com as
    duas alternativas medidas em docs/DOCUMENTACAO_GRAFICOS.md.

    Returns:
        tuple[float, float, float]: os cortes de 25%, 50% e 75%, em pontos
            percentuais de população com 60+.
    """
    base = _carregar_base()
    total = base.groupby(["ano", "uf"])["populacao"].sum()
    idosos = base[base["idade"] >= 60].groupby(["ano", "uf"])["populacao"].sum()
    pct = (idosos / total * 100).dropna()
    q = pct.quantile([0.25, 0.50, 0.75])
    return (float(q.loc[0.25]), float(q.loc[0.50]), float(q.loc[0.75]))
