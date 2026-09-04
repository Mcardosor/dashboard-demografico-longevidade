"""Orçamento de tempo por interação.

"Interação" é o trabalho completo de trocar o ano ou a seleção de estados:
processar a base do ano atual e do anterior, montar o mapa e os quatro
gráficos. É o que roda no servidor entre o clique e a resposta.

O teto é generoso de propósito. Prender o número medido faria o teste falhar
por ruído de máquina; o que ele existe para pegar é regressão de ordem de
grandeza — alguém reintroduzir a malha crua no payload, ou refazer leitura
que já estava cacheada.

O orçamento de **payload**, que é o outro lado da conta e o que de fato
travava este painel, está em `test_mapa.py`.

Os testes de teto absoluto levam a marca `tempo` e **não rodam no CI** — num
runner compartilhado a medida diz mais sobre a carga da máquina alheia do que
sobre o código. Ver a justificativa em `pytest.ini`. O que sobra no CI é a
comparação relativa, que independe da velocidade da máquina.
"""

from __future__ import annotations

import statistics
import time

import pytest

from src import charts, data, mapa
from src.themes import THEMES

#: Teto do trabalho de servidor por interação, em milissegundos. Medido em
#: cerca de 130 ms com as 27 UFs (ver docs/performance.md).
TETO_MS = 400

#: Teto de `processar_dados` sozinho, que roda duas vezes por interação.
TETO_PROCESSAR_MS = 30

REPETICOES = 3
TEMA = THEMES["light"]


@pytest.fixture(scope="module")
def base():
    ano = data.anos_disponiveis.__wrapped__()[0]
    df_raw = data.carregar_dados.__wrapped__(ano)
    df_evo = data.carregar_evolucao.__wrapped__()
    df_proc, df_idosos = charts.processar_dados(df_raw)
    return df_raw, df_evo, df_proc, df_idosos


def _mediana_ms(fn) -> float:
    fn()  # aquece
    tempos = []
    for _ in range(REPETICOES):
        inicio = time.perf_counter()
        fn()
        tempos.append((time.perf_counter() - inicio) * 1000)
    return statistics.median(tempos)


@pytest.mark.tempo
def test_interacao_completa_sob_o_orcamento(base):
    df_raw, df_evo, df_proc, df_idosos = base
    ufs = sorted(df_idosos["uf"])

    def interacao():
        charts.processar_dados(df_raw)
        charts.processar_dados(df_raw)  # ano anterior
        mapa.deck(df_idosos, TEMA)
        charts.fig_pizza(df_proc, TEMA)
        charts.fig_piramide(df_proc, TEMA)
        charts.fig_evolucao(df_evo, ufs, TEMA)

    ms = _mediana_ms(interacao)
    assert ms <= TETO_MS, f"{ms:.0f} ms"


@pytest.mark.tempo
def test_processar_dados_sob_o_orcamento(base):
    df_raw = base[0]
    ms = _mediana_ms(lambda: charts.processar_dados(df_raw))
    assert ms <= TETO_PROCESSAR_MS, f"{ms:.0f} ms"


def test_mapa_deixou_de_ser_a_figura_mais_cara(base):
    """A inversão que a troca produziu.

    O `choropleth_mapbox` custava 194 ms contra 19–28 ms de cada gráfico do
    Plotly. Depois da troca o mapa é a figura mais barata do painel. Se algum
    dia voltar a ser a mais cara, alguma das três decisões — malha
    pré-simplificada, geometria só das UFs visíveis, spec sem indentação —
    terá sido desfeita.
    """
    _, _, df_proc, df_idosos = base
    custo_mapa = _mediana_ms(lambda: mapa.deck(df_idosos, TEMA))
    custo_pizza = _mediana_ms(lambda: charts.fig_pizza(df_proc, TEMA))
    assert custo_mapa < custo_pizza


@pytest.mark.tempo
def test_geojson_carrega_rapido():
    """A malha pré-processada lê em poucos milissegundos; a crua levava 82."""
    ms = _mediana_ms(lambda: data.carregar_geojson.__wrapped__())
    assert ms <= 30, f"{ms:.0f} ms"
