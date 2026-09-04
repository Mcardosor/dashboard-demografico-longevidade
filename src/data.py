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


@st.cache_data(show_spinner=False)
def _carregar_base() -> pd.DataFrame:
    """Carrega e junta os Parquet brutos do IBGE numa base única por idade/sexo.

    Junta população, município e UF, normaliza o código de sexo do IBGE
    ("1"/"2") para "M"/"F" e garante que idade seja inteira.

    Returns:
        pd.DataFrame: colunas `uf`, `ano`, `idade`, `sexo`, `populacao`.
    """
    pop = pd.read_parquet(os.path.join(_DATA_DIR, "pop_ibge.parquet"))
    mun = pd.read_parquet(os.path.join(_DATA_DIR, "ibge_municipios.parquet"))
    ufs = pd.read_parquet(os.path.join(_DATA_DIR, "ibge_ufs.parquet"))

    pop["cod_mun"] = pop["cod_mun"].astype("int64")
    pop = (
        pop
        .merge(mun.rename(columns={"id": "cod_mun"}), on="cod_mun")
        .merge(ufs.rename(columns={"id": "ibge_uf_id"})[["ibge_uf_id", "sigla"]], on="ibge_uf_id")
    )
    pop["idade"] = pop["idade"].astype(int)
    pop["sexo"]  = pop["sexo"].map({"1": "M", "2": "F"})
    return pop[["sigla", "ano", "idade", "sexo", "populacao"]].rename(columns={"sigla": "uf"})


@st.cache_data(show_spinner=False)
def anos_disponiveis() -> list:
    """Lista os anos com dado populacional, do mais recente para o mais antigo.

    Returns:
        list: anos (int) disponíveis na base, em ordem decrescente.
    """
    return sorted(_carregar_base()["ano"].unique().tolist(), reverse=True)


@st.cache_data(show_spinner="Carregando dados populacionais…")
def carregar_dados(ano: int) -> pd.DataFrame:
    """Agrega a população de um ano específico por UF, idade e sexo.

    Args:
        ano: ano de referência (ex: 2024) presente em `anos_disponiveis()`.

    Returns:
        pd.DataFrame: colunas `uf`, `idade`, `sexo`, `populacao`, já somadas
            por município (uma linha por UF/idade/sexo).
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

    Calculados **uma vez, sobre todos os anos e todas as UFs juntos** — não
    por ano e não sobre o filtro. Os dois motivos são de leitura, não de
    implementação:

    - **Por ano não serve.** Quartil é medida relativa: recalculado a cada
      ano, ele sempre põe um quarto das UFs em cada classe. Medido: 7/6/7/7
      em 2010 e 7/6/7/7 em 2025. O mapa dos dois anos sairia igual, e o
      envelhecimento do país — que é o assunto do painel — ficaria invisível.
      Com corte fixo, 2010 tem nenhuma UF na classe mais alta e 2025 tem
      dezoito.
    - **Sobre o filtro, muito menos.** Recalcular sobre os estados
      selecionados faria os sobreviventes trocarem de cor a cada filtro. A
      cor precisa seguir o estado, não a posição dele num recorte.

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
