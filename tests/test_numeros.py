"""Os números que o painel mostra batem com a fonte?

A base é a tab1 das Projeções da População do IBGE, revisão 2024, lida por
`scripts/preparar_projecao.py`. Os números abaixo são os da planilha e das
Estimativas de População 2025 do Diário Oficial — conferidos em 04/set/2026
(base municipal antiga) e reconferidos em 15/set/2026 (base atual). Ver
docs/conferencia-dados.md e docs/levantamento-projecoes.md.

Estes testes não baixam nada: prendem os valores de referência no código,
para que uma regeração dos parquets que os mude seja notada.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.charts import IDADE_TOPO, processar_dados
from src.data import ESTIMATIVA_ATE, _carregar_base, esperanca_aos_60

#: Valores oficiais do IBGE (revisão 2024). Tab1 para população; tab4 para e60.
IBGE = {
    ("populacao", 2010): 194_749_329,
    ("populacao", 2025): 213_421_037,
    ("populacao", 2070): 199_228_708,
    ("60+", 2010): 20_718_042,
    ("60+", 2025): 35_370_902,
    ("e60_BR", 2025): 22.71,
    ("pico_BR",): 2041,
}


@pytest.fixture(scope="module")
def base() -> pd.DataFrame:
    return _carregar_base.__wrapped__()


def _ano(base, ano):
    return base[base["ano"] == ano]


# ── A base é a que o IBGE publicou ──────────────────────────────────────────

def test_cobre_2000_a_2070_nas_27_ufs(base):
    assert int(base["ano"].min()) == 2000 and int(base["ano"].max()) == 2070
    assert base["uf"].nunique() == 27


@pytest.mark.parametrize("ano", [2010, 2025, 2070])
def test_populacao_total_e_a_do_ibge(base, ano):
    assert int(_ano(base, ano)["populacao"].sum()) == IBGE[("populacao", ano)]


@pytest.mark.parametrize("ano", [2010, 2025])
def test_pessoas_com_60_mais_sao_as_do_ibge(base, ano):
    """Com a base municipal havia 4 pessoas de diferença em 2025. Com a tab1,
    que é a própria planilha do IBGE, é zero."""
    s = _ano(base, ano)
    assert int(s[s["idade"] >= 60]["populacao"].sum()) == IBGE[("60+", ano)]


def test_o_pais_atinge_o_pico_em_2041(base):
    """A história que a projeção conta e que o painel existe para mostrar."""
    br = base.groupby("ano")["populacao"].sum()
    assert int(br.idxmax()) == IBGE[("pico_BR",)]
    assert int(br.loc[2070]) < int(br.loc[2025])


def test_a_fronteira_estimativa_projecao_e_a_do_relatorio():
    """'Estimativas (2000 a 2022) e projeções (2023 a 2070)' — relatório
    metodológico da revisão 2024, capítulo 1. O ano corrente é projeção."""
    assert ESTIMATIVA_ATE == 2022


# ── O balde aberto no topo da idade ─────────────────────────────────────────

def test_base_termina_num_balde_aberto(base):
    """A idade máxima da base é o `IDADE_TOPO` da pirâmide. Se a base mudar
    (o IBGE passar a publicar até 100+), este teste avisa que a última faixa
    precisa acompanhar."""
    assert int(base["idade"].max()) == IDADE_TOPO == 90


def test_ultima_faixa_da_piramide_e_aberta(base):
    """O defeito que a primeira conferência achou: faixas desenhadas além do
    balde saem vazias e a faixa do balde sai inflada."""
    proc, _ = processar_dados(_ano(base, 2025))
    faixas = [str(f) for f in proc["faixa_etaria"].cat.categories]
    assert faixas[-1] == f"{IDADE_TOPO}+"
    assert faixas[-2] == f"{IDADE_TOPO - 5}-{IDADE_TOPO - 1}"


@pytest.mark.parametrize("ano", [2000, 2025, 2070])
def test_nenhuma_faixa_fica_vazia(base, ano):
    """Faixa desenhada e sempre zerada é rótulo que promete dado inexistente."""
    proc, _ = processar_dados(_ano(base, ano))
    soma = proc.groupby("faixa_etaria", observed=False)["populacao"].sum()
    vazias = [str(f) for f, v in soma.items() if v == 0]
    assert not vazias, f"faixas vazias em {ano}: {vazias}"


def test_faixas_somam_a_populacao(base):
    """Nenhuma pessoa se perde no corte das faixas."""
    s = _ano(base, 2025)
    proc, _ = processar_dados(s)
    assert int(proc.groupby("faixa_etaria", observed=False)["populacao"].sum().sum()) == int(s["populacao"].sum())


def test_idade_media_agora_e_a_do_ibge(base):
    """Com o balde aos 80 a média saía 36,11; o IBGE publica 36,21 para 2025.
    Com o balde aos 90 a diferença some no centésimo."""
    s = _ano(base, 2025)
    media = (s["idade"] * s["populacao"]).sum() / s["populacao"].sum()
    assert abs(media - 36.21) < 0.01


# ── Esperança de vida aos 60 ────────────────────────────────────────────────

def test_e60_do_pais_bate_com_o_oficial(base):
    """O IBGE publica o e60 do Brasil; o painel o reconstrói como média das
    UFs ponderada pela população de 60+. Tem que dar o mesmo número."""
    ufs = sorted(base["uf"].unique())
    assert abs(esperanca_aos_60(ufs, 2025) - IBGE[("e60_BR", 2025)]) < 0.05


def test_e60_cresce_no_periodo_em_toda_uf():
    """Hipótese do IBGE: a mortalidade cai em todas as UFs. Se uma UF tiver
    e60 menor em 2070 que em 2025, ou o parquet foi mal gerado ou a revisão
    mudou de hipótese — nos dois casos vale olhar."""
    from src.data import carregar_indicadores
    ind = carregar_indicadores.__wrapped__()
    for uf, s in ind.groupby("uf"):
        s = s.set_index("ano")["e60_T"]
        assert s.loc[2070] > s.loc[2025] > s.loc[2000], uf


def test_e60_de_recorte_vazio_nao_quebra():
    assert esperanca_aos_60([], 2025) == 0.0


# ── Evolução: o que a revisão de 15/set/2026 achou ──────────────────────────

def _fig_evolucao(ufs):
    from src.charts import fig_evolucao
    from src.data import carregar_evolucao
    from src.themes import THEMES
    return fig_evolucao(carregar_evolucao.__wrapped__(), ufs, THEMES["light"])


def _anotacao_do_pico(fig):
    return next(a for a in fig.layout.annotations if a.text.startswith("pico"))


@pytest.mark.parametrize("uf", ["RS", "AL", "RJ"])
def test_pico_logo_apos_a_fronteira_nao_cobre_o_rotulo(uf):
    """RS e AL viram em 2026, RJ em 2027 — a anotação do pico caía em cima de
    'projeção do IBGE →', que mora no topo, à direita de 2022."""
    a = _anotacao_do_pico(_fig_evolucao([uf]))
    assert a.xanchor == "right" and a.ay > 0, "texto à esquerda e abaixo do ponto"


def test_pico_na_borda_direita_nao_e_cortado():
    """MT ainda cresce em 2070: centrado na borda, o texto saía pela margem."""
    a = _anotacao_do_pico(_fig_evolucao(["MT"]))
    assert a.xanchor == "right"


def test_pico_no_meio_fica_centrado_acima():
    a = _anotacao_do_pico(_fig_evolucao(["SP"]))
    assert a.xanchor == "center" and a.ay < 0


def test_hover_de_2022_aparece_uma_vez_so():
    """2022 entra nas duas séries para a linha não ter buraco; no tooltip
    unificado ele aparecia duas vezes com o mesmo número."""
    fig = _fig_evolucao(["SP"])
    proj = fig.data[1]
    assert int(proj.x[0]) == ESTIMATIVA_ATE
    assert proj.hoverinfo[0] == "skip"
    assert all(h == "all" for h in proj.hoverinfo[1:])
