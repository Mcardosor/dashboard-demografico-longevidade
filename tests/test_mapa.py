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
    """`_compactar` é o que impede o recuo de dominar o payload.

    A verificação é a **quebra de linha**: o `json.dumps(indent=2)` do pydeck
    põe cada número da geometria na sua linha, e era isso que fazia o recuo
    virar três quartos do payload.

    O teste também exigia que `", "` não aparecesse. Saiu quando o mapa ganhou
    a camada de discos: o pydeck converte a lista de campos de um acessor em
    `@@=[lon, lat]` — com espaço, e é a forma correta de referenciar campo numa
    camada. Procurar `", "` media o acessor, não a indentação. O teto de bytes
    em `test_payload_*` é a guarda de verdade.
    """
    texto = mapa.deck(_dados(todas_ufs), TEMA).to_json()
    assert "\n" not in texto


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

def test_cada_tema_tem_a_sua_rampa():
    """A rampa do escuro não é o espelho da do claro.

    São degraus próprios, validados contra cada superfície com
    `scripts/validate_palette.py` do skill `dataviz`. Ver docs/identidade.md.
    """
    clara = THEMES["light"]["rampa"]
    escura = THEMES["dark"]["rampa"]
    assert clara != escura
    assert len(clara) == len(escura) == 6


def test_extremos_da_rampa():
    rampa = THEMES["light"]["rampa"]
    assert mapa._interpolar(0.0, rampa) == mapa._rgb(rampa[0])
    assert mapa._interpolar(1.0, rampa) == mapa._rgb(rampa[-1])


def _luminancia(rgb: list[int]) -> float:
    def canal(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


@pytest.mark.parametrize("modo", ["light", "dark"])
def test_rampa_vai_de_claro_a_escuro(modo):
    """Mais idosos, cor mais escura — e não o contrário.

    O mapa em Plotly ia de `#084c96` (escuro) para `#63b3ed` (claro), ou seja,
    **quanto maior a proporção, mais clara a UF**. Isso inverte a convenção de
    rampa sequencial e faz o olho ler o mapa ao avesso. A troca de paleta
    corrigiu de passagem.
    """
    rampa = THEMES[modo]["rampa"]
    lums = [_luminancia(mapa._rgb(c)) for c in rampa]
    assert lums == sorted(lums, reverse=True), "a rampa precisa escurecer"


def test_maior_proporcao_recebe_o_tom_escuro(todas_ufs):
    dados = _dados(todas_ufs)
    spec = json.loads(mapa.deck(dados, TEMA).to_json())
    feicoes = spec["layers"][0]["data"]["features"]
    por_uf = {f["properties"]["uf"]: f["properties"]["cor"] for f in feicoes}
    menor = dados.loc[dados["pct_idosos"].idxmin(), "uf"]
    maior = dados.loc[dados["pct_idosos"].idxmax(), "uf"]
    assert _luminancia(por_uf[maior]) < _luminancia(por_uf[menor])


def test_uf_unica_recebe_a_cor_da_sua_classe():
    """Com um estado só, a cor sai dos cortes fixos — não de um mínimo e um
    máximo calculados sobre ele mesmo, que não existiriam."""
    dados = _dados(["PE"])
    pct = float(dados["pct_idosos"].iloc[0])
    spec = json.loads(mapa.deck(dados, TEMA).to_json())
    feicoes = spec["layers"][0]["data"]["features"]
    assert len(feicoes) == 1
    esperada = mapa.cores_das_classes(THEMES["light"]["rampa"])[
        mapa.classificar(pct, mapa.cortes_quartis())
    ]
    assert feicoes[0]["properties"]["cor"] == esperada


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


def test_legenda_mostra_as_faixas_e_nao_os_extremos(todas_ufs):
    """A legenda anuncia os cortes fixos, não o mínimo e o máximo do recorte.

    Com escala contínua fazia sentido rotular os extremos dos dados. Com
    classes, o que o leitor precisa saber é onde cada faixa começa — e essa
    resposta não pode mudar quando ele filtra estados, senão dois mapas
    deixam de ser comparáveis.
    """
    html = mapa.legenda(_dados(todas_ufs), TEMA)
    for corte in mapa.cortes_quartis():
        assert f"{corte:.1f}".replace(".", ",") in html
    assert html.count("<span style=\"width:13px") == mapa.CLASSES


# ── Quartis ──────────────────────────────────────────────────────────────────

def test_classificar_respeita_os_cortes():
    cortes = (10.0, 20.0, 30.0)
    assert mapa.classificar(9.9, cortes) == 0
    assert mapa.classificar(10.0, cortes) == 1, "valor igual ao corte sobe"
    assert mapa.classificar(19.9, cortes) == 1
    assert mapa.classificar(30.0, cortes) == 3
    assert mapa.classificar(99.0, cortes) == 3


def test_sao_quatro_classes_distintas():
    cores = mapa.cores_das_classes(THEMES["light"]["rampa"])
    assert len(cores) == mapa.CLASSES == 4
    assert len({tuple(c) for c in cores}) == 4


def test_cortes_nao_mudam_com_o_filtro(todas_ufs):
    """A invariante que o filtro não pode quebrar.

    Se os cortes fossem recalculados sobre a seleção, escolher outro conjunto
    de estados repintaria os que continuam na tela — a cor passaria a
    descrever a posição do estado no recorte, não a proporção dele.
    """
    def cor_de(uf, ufs):
        dados = _dados(ufs)
        spec = json.loads(mapa.deck(dados, TEMA).to_json())
        for f in spec["layers"][0]["data"]["features"]:
            if f["properties"]["uf"] == uf:
                return f["properties"]["cor"]
        raise AssertionError(uf)

    alvo = todas_ufs[3]
    assert cor_de(alvo, todas_ufs) == cor_de(alvo, todas_ufs[:6])


def test_cortes_sao_crescentes_e_plausiveis():
    c = mapa.cortes_quartis()
    assert len(c) == mapa.CLASSES - 1
    assert list(c) == sorted(c)
    assert 5 < c[0] and c[-1] < 30, c


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


# ── Alvos pequenos ───────────────────────────────────────────────────────────

def _camadas(ufs):
    spec = json.loads(mapa.deck(_dados(ufs), TEMA).to_json())
    return {c["@@type"]: c for c in spec["layers"]}


def _camadas_lista(ufs):
    spec = json.loads(mapa.deck(_dados(ufs), TEMA).to_json())
    return spec["layers"]


def _ampliada(ufs):
    camadas = _camadas_lista(ufs)
    return camadas[1]["data"]["features"] if len(camadas) > 1 else []


def test_df_e_ampliado_no_mapa_do_brasil(todas_ufs):
    """No enquadramento do país o DF mede ~9x5 px — acertá-lo com o ponteiro
    é pontaria."""
    assert [f["properties"]["uf"] for f in _ampliada(todas_ufs)] == ["DF"]


def test_ampliacao_some_quando_a_uf_ja_e_grande():
    """O critério é o tamanho na tela, não a identidade da UF: com o DF
    sozinho o recorte aproxima e a ampliação perde a razão de existir."""
    assert len(_camadas_lista(["DF"])) == 1


def test_ampliacao_preserva_a_forma(todas_ufs):
    """O ponto do pedido: ampliar, não substituir por um círculo.

    A geometria ampliada precisa ser a mesma do polígono original, com o
    mesmo número de vértices — só maior.
    """
    ampliada = _ampliada(todas_ufs)[0]["geometry"]
    original = mapa._geometrias(("DF",))[0]
    assert ampliada["type"] == original["type"]
    assert len(mapa._partes([ampliada])[0]) == len(mapa._partes([original])[0])


def test_ampliacao_e_maior_e_concentrica(todas_ufs):
    """Maior que o original e em torno do mesmo centro — não deslocada."""
    ampliada = _ampliada(todas_ufs)[0]["geometry"]
    original = mapa._geometrias(("DF",))[0]
    ax0, ay0, ax1, ay1 = mapa._caixa(mapa._partes([ampliada]))
    ox0, oy0, ox1, oy1 = mapa._caixa(mapa._partes([original]))
    assert (ax1 - ax0) > (ox1 - ox0)
    assert (ax0 + ax1) / 2 == pytest.approx((ox0 + ox1) / 2, abs=1e-6)
    assert (ay0 + ay1) / 2 == pytest.approx((oy0 + oy1) / 2, abs=1e-6)


def test_ampliacao_usa_a_cor_da_classe_da_uf(todas_ufs):
    """Não pode inventar informação: é a mesma cor que o polígono original."""
    camadas = _camadas_lista(todas_ufs)
    ampliada = camadas[1]["data"]["features"][0]["properties"]["cor"]
    original = next(
        f["properties"]["cor"]
        for f in camadas[0]["data"]["features"]
        if f["properties"]["uf"] == "DF"
    )
    assert ampliada == original


def test_raio_de_captura_declarado(todas_ufs):
    """Ajuda nas bordas. Não resolve o DF — ver a constante."""
    spec = json.loads(mapa.deck(_dados(todas_ufs), TEMA).to_json())
    assert spec["pickingRadius"] == mapa.RAIO_CAPTURA


def test_disco_nao_deixa_string_virar_acessor(todas_ufs):
    """O pydeck converte string em acessor de dado (`"pixels"` -> `@@=pixels`).

    Quando isso acontece o deck procura um campo com aquele nome, não acha e
    cai no padrão — foi como o disco do DF saiu do tamanho de meio Goiás. A
    guarda é grosseira de propósito: nenhum acessor da camada de discos pode
    apontar para um nome que não é campo dos dados.
    """
    spec = json.loads(mapa.deck(_dados(todas_ufs), TEMA).to_json())
    for camada in spec["layers"]:
        for chave, valor in camada.items():
            if isinstance(valor, str) and valor.startswith("@@="):
                assert valor.startswith("@@=properties."), f"{chave}={valor}"
