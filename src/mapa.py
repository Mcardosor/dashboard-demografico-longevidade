"""Mapa coroplético da proporção de idosos por UF.

Desenhado com **pydeck**, sem basemap (`map_provider=None`).

O mapa anterior era um `plotly.express.choropleth_mapbox` sobre ladrilhos
`carto-positron`. A CARTO passou a exigir chave e o painel em produção
desenhava o carimbo "API KEY REQUIRED" repetido sob a malha. Trocar de
fornecedor de ladrilho só adiaria o problema — um coroplético por estado não
precisa de rua, rio nem nome de cidade embaixo: a informação é a cor de cada
UF. Sem ladrilho não há chave para gerenciar, nem requisição a terceiro, nem
fornecedor que possa repetir isto.

O segundo motivo é payload. O `choropleth_mapbox` recebia o GeoJSON por
parâmetro e o embutia no JSON da figura, então os 1,9 MB da malha do país
voltavam pela rede a cada rerun — inclusive com um único estado selecionado.
Aqui a geometria é pré-simplificada em disco (`scripts/preparar_geometria.py`),
só as UFs visíveis são enviadas, e o spec sai sem indentação.

Ver docs/performance.md para os números de antes e depois.
"""

from __future__ import annotations

import base64
import json
import math
from functools import lru_cache

import pandas as pd
import pydeck
import streamlit as st

from .data import carregar_geojson

#: Altura do mapa, em pixels. Era a do Plotly; mantida para não mexer no
#: alinhamento com a tabela de Top 5, que divide a linha.
ALTURA = 500

#: Largura útil da coluna do mapa, em pixels, para calcular o zoom.
#:
#: É uma estimativa, e não pode deixar de ser: o zoom é decidido no servidor e
#: a largura só existe no navegador. O `st.columns([3, 2])` dá três quintos do
#: contêiner — medido, são 853 px numa janela de 1600 e cerca de 450 numa de
#: 800.
#:
#: **Os dois erros não custam a mesma coisa.** Estimar para menos deixa margem
#: sobrando dos lados; estimar para mais faz o deck cortar a geometria. Daí o
#: valor ser o da coluna na janela mais estreita que este painel mira (~1100
#: px), e não o da janela larga.
#:
#: Para o Brasil inteiro a constante nem entra na conta: em Mercator o país
#: tem 39,2° de largura por 40,9° de altura, então quem manda é a altura, que
#: é conhecida com exatidão. Ela só decide em recortes largos e baixos.
LARGURA = 560

#: Rampa de cor, do menor para o maior. São as três paradas que o mapa em
#: Plotly já usava — a identidade visual não muda com a troca de biblioteca.
RAMPA = ("#084c96", "#2B7BB9", "#63b3ed")

#: Cor de quem não tem dado. Precisa ser distinguível de qualquer tom da rampa.
SEM_DADO = "#E5E7EB"

#: Folha de estilo **vazia**, no formato do MapLibre/Mapbox GL: sem fontes e
#: sem camadas. É o que garante que nenhum ladrilho seja pedido a ninguém.
#:
#: Não basta omitir `mapStyle` do spec. O frontend do Streamlit, quando não
#: recebe estilo, aplica o **padrão dele** — que é `mapbox://styles/...` e
#: dispara `api.mapbox.com` e `events.mapbox.com` (este último, telemetria).
#: Foi o que aconteceu em produção: trocar a CARTO por um `map_style=None`
#: trocou um fornecedor de ladrilho por outro. O `map_style=None` do pydeck
#: significa "deixe o Streamlit escolher pelo tema", e não "não desenhe mapa".
#:
#: O estilo vai como **`data:` URI**, e não como objeto. O `mapStyle` do
#: react-map-gl aceita os dois, mas o frontend do Streamlit descarta objeto e
#: cai no padrão — medido: com o objeto no spec, o navegador ainda buscava
#: `mapbox/light-v8`, sprites e fontes. Como `data:` URI o estilo é uma
#: string, sobrevive ao caminho até o componente, e o conteúdo já vem embutido:
#: nenhuma requisição sai para buscá-lo.
#:
#: Sem fontes e sem camadas, o mapbox-gl não tem o que carregar, não resolve
#: `mapbox://`, não precisa de token e não chama ninguém.
_ESTILO_VAZIO_JSON = {"version": 8, "sources": {}, "layers": []}
ESTILO_VAZIO = "data:application/json;base64," + base64.b64encode(
    json.dumps(_ESTILO_VAZIO_JSON, separators=(",", ":")).encode()
).decode()


def _rgb(cor: str) -> list[int]:
    """`#RRGGBB` para `[r, g, b]`, que é como o deck.gl espera."""
    texto = cor.lstrip("#")
    return [int(texto[i : i + 2], 16) for i in (0, 2, 4)]


def _interpolar(fracao: float) -> list[int]:
    """Cor da rampa na posição `fracao` (0 a 1), interpolada em RGB.

    Linear e contínua, como no mapa em Plotly. A proporção de idosos varia
    numa faixa estreita e bem distribuída entre as UFs (hoje 10% a 21%), então
    não há a concentração que justificaria classes por quantil — que é o que
    o sinan faz, sobre dado epidemiológico.
    """
    fracao = min(max(fracao, 0.0), 1.0)
    passos = len(RAMPA) - 1
    posicao = fracao * passos
    i = min(int(posicao), passos - 1)
    peso = posicao - i
    ini, fim = _rgb(RAMPA[i]), _rgb(RAMPA[i + 1])
    return [round(a + (b - a) * peso) for a, b in zip(ini, fim)]


def _mercator(lat: float) -> float:
    """Latitude em graus para a coordenada Y de Mercator, na mesma escala."""
    lat = min(max(lat, -85.0), 85.0)
    return math.degrees(math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)))


def _mercator_inverso(y: float) -> float:
    """Inverso de :func:`_mercator`."""
    return math.degrees(2 * math.atan(math.exp(math.radians(y))) - math.pi / 2)


#: Fração da área que define o "corpo" de um recorte. O que sobra é ilha.
COBERTURA_CORPO = 0.999

#: Quantos graus uma parte precisa estar fora do corpo para contar como
#: afastada. 1° são cerca de 110 km: mais que qualquer ilha costeira e muito
#: menos que Fernando de Noronha. Valores herdados do sinan.
FOLGA_AFASTADA = 1.0


def _partes(geometrias: list[dict]) -> list[list]:
    """Anéis externos de cada polígono, um por parte de terra."""
    saida = []
    for g in geometrias:
        coords = g["coordinates"]
        poligonos = coords if g["type"] == "MultiPolygon" else [coords]
        for poligono in poligonos:
            saida.append(poligono[0])  # anel externo; buracos não mudam bbox
    return saida


def _area(anel: list) -> float:
    """Área do anel pela fórmula do shoelace, em graus².

    Grau² não é área de verdade, e não precisa ser: serve só para ordenar
    partes do mesmo recorte, e a ordem é a mesma em qualquer projeção
    razoável.
    """
    total = 0.0
    for (x1, y1), (x2, y2) in zip(anel, anel[1:]):
        total += x1 * y2 - x2 * y1
    return abs(total) / 2


def _caixa(aneis: list[list]) -> tuple[float, float, float, float]:
    """Bounding box (xmin, ymin, xmax, ymax) de uma lista de anéis."""
    xs = [x for anel in aneis for x, _ in anel]
    ys = [y for anel in aneis for _, y in anel]
    return min(xs), min(ys), max(xs), max(ys)


def _limites(geometrias: list[dict]) -> tuple[float, float, float, float]:
    """Retângulo de enquadramento **ignorando ilhas oceânicas**.

    O bounding box cru é dominado por pedaços de terra longe de tudo, e o
    território que se quer ver encolhe para caber junto com uma ilha onde
    quase ninguém mora.

    O caso que motivou isto: **Fernando de Noronha é de Pernambuco**. O
    arquipélago fica a cerca de 350 km da costa, então o bbox cru de PE tem
    9,0° de largura contra 2,9° do estado continental — selecionar PE sozinho
    desenharia um mapa de oceano com o estado espremido num canto.

    A parte descartada some da tela. É uma perda consciente: o painel mostra
    proporção de idosos por UF, e a cor de Pernambuco continua sendo a de
    Pernambuco inteiro — o dado não muda, só o enquadramento. O sinan, que
    permite clicar no município, precisa de um quadro à parte para a ilha
    (`destacar_ilhas`); aqui não há o que clicar.
    """
    partes = _partes(geometrias)
    if len(partes) < 2:
        return _caixa(partes)

    areas = sorted(((_area(a), i) for i, a in enumerate(partes)), reverse=True)
    total = sum(a for a, _ in areas) or 1.0

    acumulado = 0.0
    corpo = []
    for area, i in areas:
        corpo.append(i)
        acumulado += area
        if acumulado / total >= COBERTURA_CORPO:
            break

    # O retângulo do corpo serve só para medir distância. Devolver ele seria
    # cortar território: ilhas costeiras caem no rabo da área e ficariam de
    # fora por uma fração de grau. O que vale é o retângulo de tudo **menos**
    # as partes distantes.
    cx0, cy0, cx1, cy1 = _caixa([partes[i] for i in corpo])
    perto = []
    for anel in partes:
        x0, y0, x1, y1 = _caixa([anel])
        distante = (
            x0 < cx0 - FOLGA_AFASTADA
            or x1 > cx1 + FOLGA_AFASTADA
            or y0 < cy0 - FOLGA_AFASTADA
            or y1 > cy1 + FOLGA_AFASTADA
        )
        if not distante:
            perto.append(anel)

    return _caixa(perto or partes)


def enquadrar(limites, largura: int = LARGURA, altura: int = ALTURA) -> dict:
    """Centro e zoom que fazem os limites caberem na tela.

    O eixo vertical é medido em Mercator, não em graus. Tratar grau de
    latitude como grau de longitude estoura a borda de baixo nos recortes ao
    sul — é o mesmo cuidado registrado no `enquadrar` do sinan.

    O mapa fixo do Plotly ficava sempre em `zoom=3.2` centrado no Brasil,
    mesmo com uma UF só selecionada. Aqui o enquadramento acompanha o filtro.
    """
    xmin, ymin, xmax, ymax = limites
    centro = {
        "lon": (xmin + xmax) / 2,
        "lat": _mercator_inverso((_mercator(ymin) + _mercator(ymax)) / 2),
    }

    dx = xmax - xmin
    dy = abs(_mercator(ymax) - _mercator(ymin))

    escalas = [largura / dx] if dx > 0 else []
    if dy > 0:
        escalas.append(altura / dy)
    if not escalas:
        return {"center": centro, "zoom": 6.0}

    # 512 e não 256: o deck.gl usa tile de 512px, ao contrário do Leaflet. A
    # folga de 0,05 é maior do que a conta pediria — errar para o lado da
    # margem é melhor do que cortar a geometria.
    zoom = math.log2(min(escalas) * 360 / 512) - 0.05
    return {"center": centro, "zoom": max(2.0, min(zoom, 10.0))}


@st.cache_resource(show_spinner=False)
def _indice() -> dict[str, dict]:
    """Geometria por sigla, lida uma vez por processo.

    Fica separado dos dados de propósito. A geometria não muda quando o
    usuário troca de ano, de estado ou de tema; cor e valor mudam a cada
    interação. Guardar as duas coisas juntas serviria mapa velho — é o erro
    que o sinan registra em `mapa._geometrias`.
    """
    colecao = carregar_geojson()
    return {
        f["properties"]["sigla"]: f["geometry"]
        for f in colecao["features"]
    }


@lru_cache(maxsize=64)
def _geometrias(ufs: tuple[str, ...]) -> list[dict]:
    """Geometrias das UFs pedidas, na ordem pedida.

    Memoizado por recorte: os filtros de região do painel são poucos e
    repetidos, e recortar o índice a cada rerun é trabalho idêntico.
    """
    indice = _indice()
    return [indice[uf] for uf in ufs if uf in indice]


def _compactar(mapa_deck: pydeck.Deck) -> None:
    """Fixa o spec final: sem indentação e sem basemap.

    O `pydeck.serialize` chama ``json.dumps(..., indent=2)`` e o
    ``st.pydeck_chart`` envia ao navegador exatamente o que ``to_json()``
    devolver. Com geometria — listas aninhadas de coordenadas — cada número
    ganha sua linha e seu recuo, e o espaço em branco vira a maior parte do
    que trafega. O sinan mediu 2,76 MB dos quais 2,0 MB eram recuo.

    Substituir o método na instância é feio, mas é o único ponto de entrada:
    o Streamlit não expõe opção de serialização e o pydeck não parametriza o
    `indent`. Se a API interna mudar, o `except` devolve o comportamento
    padrão — payload grande, nunca página quebrada.
    """
    try:
        from pydeck.bindings.json_tools import default_serialize

        spec = json.loads(json.dumps(mapa_deck, default=default_serialize))
        # O pydeck recusa `map_style` como dict a menos que o provedor seja
        # "mapbox", então o estilo vazio entra aqui, onde o spec final já é
        # nosso. Ver ESTILO_VAZIO para o porquê de ele ser necessário.
        spec["mapStyle"] = ESTILO_VAZIO
        compacto = json.dumps(spec, sort_keys=True, separators=(",", ":"))
    # Captura ampla de propósito: otimização não pode derrubar o mapa. E
    # `Exception`, nunca `BaseException` — `RerunException` herda desta última
    # justamente para atravessar blocos como este.
    except Exception:
        return

    mapa_deck.to_json = lambda: compacto


def deck(df_idosos: pd.DataFrame, t: dict) -> pydeck.Deck:
    """Monta o mapa coroplético das UFs presentes em `df_idosos`.

    Args:
        df_idosos: uma linha por UF, com `uf`, `pct_idosos`, `idosos` e
            `total` (ver `src.charts.processar_dados`), já filtrado pela
            seleção de estados.
        t: dicionário de tema (cores) atual.

    Returns:
        pydeck.Deck: mapa sem basemap, enquadrado nas UFs recebidas.
    """
    ufs = tuple(df_idosos["uf"])
    geometrias = _geometrias(ufs)

    valores = df_idosos["pct_idosos"]
    minimo = float(valores.min()) if len(valores) else 0.0
    maximo = float(valores.max()) if len(valores) else 0.0
    faixa = maximo - minimo

    feicoes = []
    for geometria, (_, linha) in zip(geometrias, df_idosos.iterrows()):
        pct = float(linha["pct_idosos"])
        cor = _interpolar((pct - minimo) / faixa) if faixa > 0 else _rgb(RAMPA[1])
        feicoes.append({
            "type": "Feature",
            "geometry": geometria,
            "properties": {
                "uf": linha["uf"],
                "pct": f"{pct:.2f}%",
                "idosos": f"{int(linha['idosos']):,}".replace(",", "."),
                "total": f"{int(linha['total']):,}".replace(",", "."),
                "cor": cor,
            },
        })

    camada = pydeck.Layer(
        "GeoJsonLayer",
        data={"type": "FeatureCollection", "features": feicoes},
        stroked=True,
        filled=True,
        get_fill_color="properties.cor",
        get_line_color=_rgb(t["map_line"]) if t.get("map_line", "").startswith("#") else [255, 255, 255],
        line_width_min_pixels=0.8,
        pickable=True,
        auto_highlight=True,
    )

    quadro = enquadrar(_limites(geometrias)) if geometrias else {
        "center": {"lat": -14.24, "lon": -51.93}, "zoom": 3.2,
    }

    mapa_deck = pydeck.Deck(
        layers=[camada],
        initial_view_state=pydeck.ViewState(
            latitude=quadro["center"]["lat"],
            longitude=quadro["center"]["lon"],
            zoom=quadro["zoom"],
            bearing=0,
            pitch=0,
            height=ALTURA,
        ),
        map_provider=None,
        # `map_style=None` tira do spec o sentinela `__MAP_STYLE__` que o
        # pydeck emitiria — uma string que o deck.gl busca como URL relativa
        # a cada render, recebendo o `index.html` do Streamlit e enchendo o
        # console de "Unexpected token '<'".
        #
        # Mas `None` **não** significa "sem mapa": o Streamlit entende como
        # "escolha o estilo pelo tema" e aplica o dele, que é Mapbox. Quem
        # de fato remove o basemap é o ESTILO_VAZIO injetado em `_compactar`.
        map_style=None,
        tooltip={
            "html": (
                "<b>{uf}</b><br>% Idosos: {pct}<br>"
                "Idosos: {idosos}<br>Total: {total}"
            ),
            "style": {
                "backgroundColor": "rgba(17,24,39,.96)",
                "color": "#fff",
                "fontSize": "12px",
                "borderRadius": "10px",
                "padding": "6px 8px",
            },
        },
    )
    _compactar(mapa_deck)
    return mapa_deck


def legenda(df_idosos: pd.DataFrame, t: dict) -> str:
    """HTML da legenda de cor.

    O deck.gl não tem barra de cor como o Plotly tinha; a rampa é desenhada
    com um `linear-gradient` em CSS, que custa zero byte de payload.
    """
    valores = df_idosos["pct_idosos"]
    if not len(valores):
        return ""
    minimo, maximo = float(valores.min()), float(valores.max())
    paradas = ", ".join(RAMPA)
    return f"""
    <div style="display:flex;align-items:center;gap:10px;margin-top:8px;
                font-size:.78rem;color:{t['text_muted']}">
      <span>% Idosos</span>
      <span>{minimo:.1f}%</span>
      <div style="flex:1;height:10px;border-radius:5px;
                  border:1px solid {t['border']};
                  background:linear-gradient(to right, {paradas})"></div>
      <span>{maximo:.1f}%</span>
    </div>
    """
