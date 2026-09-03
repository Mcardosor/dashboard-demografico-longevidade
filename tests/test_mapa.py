"""O mapa: payload, enquadramento, cor e ausência de fornecedor de ladrilho.

O teto de payload é o teste mais importante do arquivo. O mapa antigo
despachava 1.953 KB a cada rerun — em qualquer recorte, inclusive com um
estado só — e nenhum teste apontava, porque payload não muda resultado, só
custo. Ver docs/performance.md.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from src import mapa
from src.themes import THEMES
from src.utils import REGIOES

TEMA = THEMES["light"]

#: Teto do payload do mapa, em KB, com as 27 UFs. Hoje são 98.
TETO_KB_BRASIL = 200

#: Teto com uma UF só. Hoje são 3. Prende o ganho que motivou a troca: quem
#: olha um estado não paga mais pela malha do país.
TETO_KB_UMA_UF = 20


def _dados(ufs: list[str]) -> pd.DataFrame:
    """Um `df_idosos` sintético, com um gradiente de `pct_idosos`."""
    return pd.DataFrame({
        "uf": ufs,
        "total": [1_000_000] * len(ufs),
        "idosos": [100_000 + i * 10_000 for i in range(len(ufs))],
        "pct_idosos": [10.0 + i for i in range(len(ufs))],
    })


@pytest.fixture(scope="module")
def todas_ufs() -> list[str]:
    return sorted(mapa._indice.__wrapped__())


def _payload_kb(deck) -> float:
    return len(deck.to_json().encode("utf-8")) / 1024


# ── Payload ──────────────────────────────────────────────────────────────────

def test_payload_do_brasil_sob_o_teto(todas_ufs):
    kb = _payload_kb(mapa.deck(_dados(todas_ufs), TEMA))
    assert kb <= TETO_KB_BRASIL, f"{kb:.0f} KB"


def test_payload_de_uma_uf_sob_o_teto():
    kb = _payload_kb(mapa.deck(_dados(["PE"]), TEMA))
    assert kb <= TETO_KB_UMA_UF, f"{kb:.0f} KB"


def test_payload_acompanha_o_filtro(todas_ufs):
    """O defeito central do mapa antigo: o payload não respondia ao filtro."""
    brasil = _payload_kb(mapa.deck(_dados(todas_ufs), TEMA))
    uma = _payload_kb(mapa.deck(_dados(["PE"]), TEMA))
    assert uma < brasil / 5


def test_spec_sai_sem_indentacao(todas_ufs):
    """`_compactar` é o que impede o recuo de dominar o payload."""
    texto = mapa.deck(_dados(todas_ufs), TEMA).to_json()
    assert "\n" not in texto
    assert ", " not in texto


# ── Sem fornecedor de ladrilho ───────────────────────────────────────────────

def test_nao_pede_ladrilho_a_ninguem(todas_ufs):
    """O motivo da troca: a CARTO passou a exigir chave e o painel desenhava
    "API KEY REQUIRED" sob a malha. Nada de basemap deve reaparecer."""
    spec = json.loads(mapa.deck(_dados(todas_ufs), TEMA).to_json())
    texto = json.dumps(spec).lower()
    for fornecedor in ("carto", "mapbox", "openstreetmap", "maptiler", "basemaps"):
        assert fornecedor not in texto
    assert not spec.get("mapProvider")

    # O que este teste **não** alcança: o basemap que o frontend do Streamlit
    # acrescenta por conta própria quando o spec não manda estilo. Isso não
    # aparece no JSON e só se vê no painel de rede do navegador — foi assim
    # que passou despercebido. Quem cobre esse flanco é
    # `test_estilo_vazio_e_explicito`.


def test_nao_emite_o_sentinela_de_estilo(todas_ufs):
    """Sem `map_style=None` explícito, o pydeck deixa `__MAP_STYLE__` no spec
    e o deck.gl o busca como URL relativa a cada render — 200 com o
    `index.html` do Streamlit, e "Unexpected token '<'" no console."""
    spec = json.loads(mapa.deck(_dados(todas_ufs), TEMA).to_json())
    assert spec.get("mapStyle") != "__MAP_STYLE__"


def test_estilo_vazio_e_explicito(todas_ufs):
    """O spec traz uma folha de estilo vazia, e não a ausência de estilo.

    Este teste nasceu de um defeito que chegou em produção. A versão anterior
    apenas **omitia** `mapStyle`, e o teste checava a omissão — o que passava
    enquanto o painel no ar desenhava um basemap do Mapbox por baixo da
    malha, porque sem estilo o Streamlit aplica o padrão dele.

    Estilo vazio é uma afirmação; ausência de estilo é um convite ao padrão
    alheio.
    """
    import base64

    spec = json.loads(mapa.deck(_dados(todas_ufs), TEMA).to_json())
    estilo = spec["mapStyle"]

    # String, e não objeto: o frontend do Streamlit descarta objeto e cai no
    # padrão dele, que é Mapbox. Medido no painel de rede.
    assert isinstance(estilo, str), "estilo como objeto volta a puxar Mapbox"
    assert estilo.startswith("data:application/json;base64,"), estilo[:60]

    # `data:` e não URL: o conteúdo vem embutido, então nem para buscar o
    # estilo sai requisição.
    conteudo = json.loads(base64.b64decode(estilo.split(",", 1)[1]))
    assert conteudo["sources"] == {}, "fonte de ladrilho no estilo"
    assert conteudo["layers"] == [], "camada de basemap no estilo"


# ── Enquadramento ────────────────────────────────────────────────────────────

def _cabe(ufs: list[str]) -> bool:
    """A geometria do recorte cabe na caixa do mapa com o zoom calculado?"""
    geometrias = mapa._geometrias(tuple(ufs))
    xmin, ymin, xmax, ymax = mapa._limites(geometrias)
    quadro = mapa.enquadrar((xmin, ymin, xmax, ymax))

    # px por grau no zoom devolvido, na convenção de tile de 512px do deck.gl.
    px_por_grau = 2 ** quadro["zoom"] * 512 / 360
    largura = (xmax - xmin) * px_por_grau
    altura = abs(mapa._mercator(ymax) - mapa._mercator(ymin)) * px_por_grau
    return largura <= mapa.LARGURA and altura <= mapa.ALTURA


def test_brasil_cabe_na_caixa(todas_ufs):
    assert _cabe(todas_ufs)


@pytest.mark.parametrize("regiao", sorted(REGIOES))
def test_cada_regiao_cabe_na_caixa(regiao):
    assert _cabe(REGIOES[regiao]), regiao


@pytest.mark.parametrize("uf", ["PE", "RR", "SP", "RS", "AM", "DF"])
def test_cada_uf_sozinha_cabe_na_caixa(uf):
    assert _cabe([uf]), uf


def test_zoom_acompanha_o_recorte(todas_ufs):
    """O mapa em Plotly ficava em `zoom=3.2` fixo, mesmo com uma UF só."""
    brasil = mapa.enquadrar(mapa._limites(mapa._geometrias(tuple(todas_ufs))))
    pe = mapa.enquadrar(mapa._limites(mapa._geometrias(("PE",))))
    assert pe["zoom"] > brasil["zoom"] + 1


def test_centro_cai_dentro_do_recorte():
    quadro = mapa.enquadrar(mapa._limites(mapa._geometrias(("PE",))))
    xmin, ymin, xmax, ymax = mapa._limites(mapa._geometrias(("PE",)))
    assert xmin <= quadro["center"]["lon"] <= xmax
    assert ymin <= quadro["center"]["lat"] <= ymax


# ── Cor ──────────────────────────────────────────────────────────────────────

def test_rampa_preserva_as_cores_do_plotly():
    """A troca de biblioteca não mexe na identidade visual: são as três
    paradas que o `color_continuous_scale` já usava."""
    assert mapa.RAMPA == ("#084c96", "#2B7BB9", "#63b3ed")


def test_extremos_da_rampa():
    assert mapa._interpolar(0.0) == mapa._rgb("#084c96")
    assert mapa._interpolar(1.0) == mapa._rgb("#63b3ed")
    assert mapa._interpolar(0.5) == mapa._rgb("#2B7BB9")


def test_menor_proporcao_recebe_o_tom_escuro(todas_ufs):
    """Como no mapa antigo: menos idosos, azul mais escuro."""
    dados = _dados(todas_ufs)
    spec = json.loads(mapa.deck(dados, TEMA).to_json())
    feicoes = spec["layers"][0]["data"]["features"]
    por_uf = {f["properties"]["uf"]: f["properties"]["cor"] for f in feicoes}
    menor = dados.loc[dados["pct_idosos"].idxmin(), "uf"]
    maior = dados.loc[dados["pct_idosos"].idxmax(), "uf"]
    assert por_uf[menor] == mapa._rgb("#084c96")
    assert por_uf[maior] == mapa._rgb("#63b3ed")


def test_uf_unica_nao_divide_por_zero():
    """Com um estado só, mínimo e máximo coincidem."""
    spec = json.loads(mapa.deck(_dados(["PE"]), TEMA).to_json())
    feicoes = spec["layers"][0]["data"]["features"]
    assert len(feicoes) == 1
    assert feicoes[0]["properties"]["cor"] == mapa._rgb(mapa.RAMPA[1])


# ── Conteúdo ─────────────────────────────────────────────────────────────────

def test_uma_feicao_por_uf_selecionada():
    ufs = REGIOES["Sudeste"]
    spec = json.loads(mapa.deck(_dados(ufs), TEMA).to_json())
    feicoes = spec["layers"][0]["data"]["features"]
    assert {f["properties"]["uf"] for f in feicoes} == set(ufs)


def test_tooltip_traz_os_quatro_valores(todas_ufs):
    """O tooltip vive no objeto, fora do `to_json()` — é de lá que o
    Streamlit o lê. Importa porque `_compactar` substitui o `to_json`, e
    isso não pode levar o tooltip junto."""
    html = mapa.deck(_dados(todas_ufs), TEMA)._tooltip["html"]
    for campo in ("{uf}", "{pct}", "{idosos}", "{total}"):
        assert campo in html


def test_geometria_memoizada_por_recorte():
    """A geometria não muda quando ano, tema ou métrica mudam."""
    mapa._geometrias.cache_clear()
    primeira = mapa._geometrias(("PE", "BA"))
    segunda = mapa._geometrias(("PE", "BA"))
    assert primeira is segunda
    assert mapa._geometrias.cache_info().hits == 1


def test_legenda_mostra_os_extremos(todas_ufs):
    dados = _dados(todas_ufs)
    html = mapa.legenda(dados, TEMA)
    assert f"{dados['pct_idosos'].min():.1f}%" in html
    assert f"{dados['pct_idosos'].max():.1f}%" in html


# ── Ilhas oceânicas ──────────────────────────────────────────────────────────

def test_noronha_nao_domina_o_enquadramento_de_pe():
    """Fernando de Noronha é de Pernambuco e fica a ~350 km da costa. Sem
    descartá-la, o bbox de PE vai a 9,0° de largura contra os 6,5° do estado
    continental — o mapa perderia mais de um quarto da escala para desenhar
    oceano. Os mesmos 9,0° e 6,6° estão medidos em
    `paineis/sinan/docs/performance.md`, sobre a malha municipal."""
    geometrias = mapa._geometrias(("PE",))
    cru = mapa._caixa(mapa._partes(geometrias))
    util = mapa._limites(geometrias)
    assert (cru[2] - cru[0]) == pytest.approx(9.0, abs=0.3)
    assert (util[2] - util[0]) == pytest.approx(6.5, abs=0.3)
    assert util[2] < -34.0, "Noronha continua puxando a borda leste"


def test_ilha_costeira_nao_e_descartada():
    """A folga é de 1° (~110 km): separa Noronha do continente sem recortar
    ilha costeira, que é território contíguo na prática."""
    geometrias = mapa._geometrias(("SP",))
    cru = mapa._caixa(mapa._partes(geometrias))
    util = mapa._limites(geometrias)
    assert util == pytest.approx(cru, abs=0.5)


def test_recorte_de_uma_parte_so_nao_quebra():
    """O DF é um polígono único — o caminho curto de `_limites`."""
    assert mapa._limites(mapa._geometrias(("DF",)))
