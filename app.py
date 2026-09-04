"""
app.py — Dashboard Demográfico Longevidade (Streamlit + Plotly + pydeck).

Distribuição etária, proporção de pessoas com 60 anos ou mais e evolução
populacional por estado, a partir das Projeções de População do IBGE
(2010-2025).

O coroplético é o único gráfico fora do Plotly: mora em `src/mapa.py`, é
desenhado com pydeck e não usa basemap. O porquê está em docs/performance.md.
"""

import streamlit as st
import streamlit.components.v1  # noqa: F401  (usado como st.components.v1)

from src.themes import (THEMES, _css, inject_toggle, marca_html, ROXO_MARCA,
                        script_travar_zoom)
from src.data import anos_disponiveis, carregar_dados, carregar_evolucao, carregar_geojson
from src.charts import processar_dados, fig_pizza, fig_piramide, fig_evolucao
from src import mapa
from src.utils import PLOTLY_CFG, REGIOES, _fmt, _delta_html, kpi_card, section_header, html_top5

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Envelhecimento Populacional | Longevidade",
    page_icon="🗺️",
    layout="wide",
    # Sem barra lateral: os filtros vivem numa linha no corpo da página.
)


# ── Warmup: pré-aquece cache na inicialização ──────────────────────────────
@st.cache_resource(show_spinner=False)
def _iniciar_warmup():
    """Roda uma vez por processo — pré-carrega dados mais comuns em background."""
    import threading
    def _bg():
        """Alvo da thread de warmup: pré-carrega geojson, evolução e o ano mais recente."""
        try:
            from src.data import carregar_dados, carregar_evolucao, carregar_geojson
            carregar_geojson()
            carregar_evolucao()
            anos = anos_disponiveis()
            if anos:
                carregar_dados(anos[0])
        except Exception:
            pass
    threading.Thread(target=_bg, daemon=True).start()
    return True
_iniciar_warmup()
# ───────────────────────────────────────────────────────────────────────────

if "theme" not in st.session_state:
    st.session_state.theme = "light"

# O dicionário do tema é resolvido **antes** da sidebar, que também pinta
# widget com a cor da marca. O CSS global continua sendo injetado mais abaixo,
# depois dos filtros, porque a ordem de injeção importa para o Streamlit.
t = THEMES[st.session_state.theme]

carregar_geojson()  # aquece o cache da malha antes do primeiro render
_anos   = anos_disponiveis()

# ── Dados carregados antes da sidebar ─────────────────────────────────────────
# Carrega com ano padrão para ter ufs_disponiveis na sidebar
_ano_default = st.session_state.get("ano_sel", _anos[0])
_df_default  = carregar_dados(_ano_default)
_ufs_disp    = sorted(_df_default["uf"].unique().tolist())

# ── Tema ──────────────────────────────────────────────────────────────────────
st.markdown(_css(t), unsafe_allow_html=True)

# Esconde o iframe do componente que injeta o botão de tema — ele não tem
# conteúdo visível, só script.
#
# O seletor era `iframe[height='50']`. O Streamlit 1.63 parou de emitir o
# atributo `height`, o seletor deixou de casar e o iframe apareceu na página.
# `data-testid="stIFrame"` é o identificador estável; o antigo fica junto para
# o caso de uma versão anterior. Se algum dia o painel usar `components.html`
# para algo visível, esta regra precisa ser restringida.
st.markdown(
    "<style>iframe[data-testid='stIFrame'], iframe[height='50']"
    "{display:none!important;margin:0;padding:0;height:0!important}</style>",
    unsafe_allow_html=True,
)
inject_toggle()
if st.session_state.theme == "light":
    # O wordmark reproduz o logo oficial: "Plataforma" leve por cima,
    # "Longevidade" pesado, com a flor de cinco pétalas no lugar do "o".
    #
    # Na barra roxa a flor é **branca com o miolo roxo**, e não magenta como
    # no arquivo original: #AA2DA3 sobre #6B2F96 empasta — são dois roxos
    # vizinhos. Assim a forma se preserva e o contraste funciona. O magenta
    # continua sendo o acento da marca (`accent2`) onde há fundo claro.
    st.markdown(
        f'<div class="marca-bar">{marca_html("Envelhecimento Populacional")}</div>',
        unsafe_allow_html=True,
    )

# ── Filtros ──────────────────────────────────────────────────────────────────
# Numa linha, logo abaixo do título e acima do que eles mudam.
#
# Eram três controles numa barra lateral: um checkbox "Todos os estados", um
# seletor de região que só aparecia ao desmarcá-lo, e um multiselect que só
# aparecia se a região fosse "nenhum". Três controles encadeados para uma
# escolha só, escondidos num painel que o leitor precisava abrir — e que
# roubava um quinto da largura do painel.
#
# Aqui a escolha do recorte é **um** seletor: todos, uma região, ou estados a
# dedo. O multiselect só aparece na última opção.
RECORTE_TODOS = "Todos os estados"
RECORTE_ESCOLHER = "Escolher estados…"

_hero = st.container()  # reservado: o título vai acima dos filtros, mas
                        # precisa dos valores que eles produzem

col_ano, col_recorte, col_estados = st.columns([1, 1.2, 2.4], gap="medium")

with col_ano:
    ano_sel = st.selectbox("Ano de referência", options=_anos, index=0, key="ano_sel")
    ano_ant = _anos[_anos.index(ano_sel) + 1] if _anos.index(ano_sel) + 1 < len(_anos) else None

with col_recorte:
    recorte = st.selectbox(
        "Recorte",
        options=[RECORTE_TODOS, *REGIOES, RECORTE_ESCOLHER],
        key="sel_recorte",
    )

with col_estados:
    if recorte == RECORTE_ESCOLHER:
        ufs_sel = st.multiselect(
            "Estados", options=_ufs_disp, key="ms_ufs",
            placeholder="Nenhum escolhido mostra todos",
        ) or _ufs_disp
    elif recorte == RECORTE_TODOS:
        ufs_sel = _ufs_disp
        st.markdown("<div style='height:1.8rem'></div>", unsafe_allow_html=True)
        st.caption(f"{len(ufs_sel)} estados, o país inteiro.")
    else:
        ufs_sel = [u for u in REGIOES[recorte] if u in _ufs_disp]
        st.markdown("<div style='height:1.8rem'></div>", unsafe_allow_html=True)
        st.caption(f"{recorte}: {', '.join(ufs_sel)}.")

# ── Dados ─────────────────────────────────────────────────────────────────────
df_raw             = carregar_dados(ano_sel)
df_proc, df_idosos = processar_dados(df_raw)
df_evo             = carregar_evolucao()

df_ant                     = carregar_dados(ano_ant) if ano_ant else None
df_proc_ant, df_idosos_ant = processar_dados(df_ant) if df_ant is not None else (None, None)

pop_total = int(df_proc["populacao"].sum())
n_ufs     = df_proc["uf"].nunique()

# ── Métricas filtradas ────────────────────────────────────────────────────────
df_filt    = df_proc[df_proc["uf"].isin(ufs_sel)]
df_id_filt = df_idosos[df_idosos["uf"].isin(ufs_sel)]

def _indicadores(d):
    """Os quatro números dos KPIs, para um recorte de UFs e um ano.

    Devolve zeros num recorte vazio em vez de dividir por zero.
    """
    total = int(d["populacao"].sum())
    if not total:
        return dict(total=0, n60=0, pct60=0.0, indice=0.0, idade=0.0)
    n60 = int(d[d["idade"] >= 60]["populacao"].sum())
    criancas = int(d[d["idade"] <= 14]["populacao"].sum())
    return dict(
        total=total,
        n60=n60,
        pct60=n60 / total * 100,
        # Índice de envelhecimento: pessoas de 60+ para cada 100 crianças de
        # 0 a 14 anos. É o indicador clássico da transição demográfica, e o
        # que mais se move aqui — 43 em 2010, 85 em 2025.
        indice=(n60 / criancas * 100) if criancas else 0.0,
        idade=(d["idade"] * d["populacao"]).sum() / total,
    )


atual = _indicadores(df_filt)
anterior = (
    _indicadores(df_proc_ant[df_proc_ant["uf"].isin(ufs_sel)])
    if df_proc_ant is not None
    else dict(total=0, n60=0, pct60=0.0, indice=0.0, idade=0.0)
)
pop_filt = atual["total"]

# ── Hero ──────────────────────────────────────────────────────────────────────
_label_ufs = (
    "Todos os estados" if len(ufs_sel) == n_ufs
    else f"{len(ufs_sel)} estado{'s' if len(ufs_sel) > 1 else ''} selecionado{'s' if len(ufs_sel) > 1 else ''}"
)

_hero.markdown(f"""
<div class="hero">
  <h1 class="hero-title">Envelhecimento Populacional no Brasil</h1>
  <p class="hero-subtitle">
    Distribuição etária, proporção de pessoas com 60 anos ou mais e
    evolução histórica da população, por estado. Fonte: Projeções de
    População do IBGE.
  </p>
  <div class="hero-badges">
    <span class="hero-badge accent"><span class="dot"></span>{_label_ufs}</span>
    <span class="hero-badge success"><span class="dot"></span>{_fmt(pop_filt)} pessoas</span>
    <span class="hero-badge"><span class="dot"></span>IBGE · {ano_sel}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── KPIs ──────────────────────────────────────────────────────────────────────
# Os quatro cards são facetas do MESMO assunto, então usam a mesma cor de
# marca. Antes cada um tinha um matiz (azul, laranja, roxo, verde) que não
# codificava nada — cor decorativa, que o olho tenta interpretar e não
# encontra significado.
#
# Saiu "Proporção feminina": 51,09% em 2010 contra 51,25% em 2025, ou seja,
# 0,16 ponto em quinze anos. O "▲ 0,0% vs ano anterior" não era do ano, era
# do indicador — e proporção de mulheres na população total não fala de
# envelhecimento. Entrou o índice de envelhecimento, que dobrou no período.
kpi_items = [
    ("🧓", "Pessoas com 60+", _fmt(atual["n60"]),
     f"de {_fmt(atual['total'])} habitantes",
     _delta_html(atual["n60"], anterior["n60"])),
    ("📊", "Proporção de 60+", f"{atual['pct60']:.1f}%",
     "da população total",
     _delta_html(atual["pct60"], anterior["pct60"])),
    ("⚖️", "Índice de envelhecimento", f"{atual['indice']:.0f}",
     "60+ para cada 100 crianças (0–14)",
     _delta_html(atual["indice"], anterior["indice"])),
    ("📅", "Idade média", f"{atual['idade']:.1f} anos",
     "média ponderada",
     _delta_html(atual["idade"], anterior["idade"])),
]

cols = st.columns(4)
for col, (icon, title, value, sub, delta) in zip(cols, kpi_items):
    with col:
        st.markdown(kpi_card(title, value, sub, icon, delta), unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)
st.divider()

# ── 01 · Mapa + 02 · Estados mais envelhecidos ──────────────────────────────
col_mapa, col_top5 = st.columns([3, 2])

with col_mapa:
    st.markdown(section_header("01", "Onde estão os 60+",
        "Percentual da população com 60 anos ou mais em cada estado."), unsafe_allow_html=True)
    st.pydeck_chart(mapa.deck(df_id_filt, t), use_container_width=True)
    st.markdown(mapa.legenda(df_id_filt, t), unsafe_allow_html=True)
    # Altura 0: o componente só carrega script, não desenha nada.
    st.components.v1.html(script_travar_zoom(), height=0)

with col_top5:
    st.markdown(section_header("02", "Estados mais envelhecidos",
        "Os 15 primeiros, com o valor exato que o mapa não mostra."), unsafe_allow_html=True)
    top_n = min(15, len(df_id_filt))
    top15 = (
        df_id_filt[["uf", "pct_idosos", "idosos"]]
        .sort_values("pct_idosos", ascending=False).head(top_n)
        .rename(columns={"uf": "UF", "pct_idosos": "% 60+", "idosos": "Pessoas 60+"})
        .reset_index(drop=True)
    )
    top15["% 60+"]       = top15["% 60+"].map("{:.2f}%".format)
    top15["Pessoas 60+"] = top15["Pessoas 60+"].map("{:,.0f}".format)
    st.markdown(html_top5(top15, t), unsafe_allow_html=True)

st.divider()

# ── 03 · Homens e mulheres + 04 · Pirâmide etária ────────────────────────────
col_pizza, col_piramide = st.columns([1, 1], gap="large")

with col_pizza:
    st.markdown(section_header("03", "Homens e mulheres",
        "Composição por sexo; o toggle restringe às pessoas de 60 anos ou mais."),
        unsafe_allow_html=True)
    filtrar_idosos_pizza = st.toggle("Apenas ≥ 60 anos", value=False)
    st.plotly_chart(fig_pizza(df_filt, t, filtrar_idosos_pizza), use_container_width=True, config=PLOTLY_CFG)

with col_piramide:
    st.markdown(section_header("04", "Pirâmide etária",
        "Distribuição por faixa de 5 anos e sexo. Base larga = pop. jovem · Topo largo = pop. envelhecida."),
        unsafe_allow_html=True)
    st.plotly_chart(fig_piramide(df_filt, t), use_container_width=True, config=PLOTLY_CFG)

st.divider()

# ── 05 · Evolução ────────────────────────────────────────────────────────────
# Ocupa a linha inteira desde que o ranking saiu. Ele mostrava a mesma
# proporção por UF que o mapa (01) e a tabela (02) — o mesmo número em três
# formas, e era o que fazia os títulos soarem repetidos.
st.markdown(section_header("05", "Evolução populacional — 2010 a 2025",
    "Total de habitantes nos estados selecionados ao longo dos anos."), unsafe_allow_html=True)
st.plotly_chart(fig_evolucao(df_evo, ufs_sel, t), use_container_width=True, config=PLOTLY_CFG)

st.divider()

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="marca-footer" style="
    background:{ROXO_MARCA};
    border-radius:12px;
    padding:28px 36px;
    margin-top:8px;
">
    <div style="font-size:1.25rem;margin-bottom:6px;">{marca_html()}</div>
    <div style="font-size:.82rem;color:rgba(255,255,255,.75);">
        Observatório da Longevidade · Universidade de Brasília
    </div>
</div>
""", unsafe_allow_html=True)
