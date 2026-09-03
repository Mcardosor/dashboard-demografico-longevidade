"""
app.py — Dashboard Demográfico Longevidade (Streamlit + Plotly + pydeck).

Distribuição etária, proporção de idosos e evolução populacional por
estado, a partir das Projeções de População do IBGE (2010-2025).

O coroplético é o único gráfico fora do Plotly: mora em `src/mapa.py`, é
desenhado com pydeck e não usa basemap. O porquê está em docs/performance.md.
"""

import streamlit as st

from src.themes import THEMES, _css, inject_toggle
from src.data import anos_disponiveis, carregar_dados, carregar_evolucao, carregar_geojson
from src.charts import processar_dados, fig_pizza, fig_piramide, fig_ranking, fig_evolucao
from src import mapa
from src.utils import PLOTLY_CFG, REGIOES, _fmt, _delta_html, kpi_card, section_header, html_top5

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Demográfico | Longevidade",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
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

carregar_geojson()  # aquece o cache da malha antes do primeiro render
_anos   = anos_disponiveis()

# ── Dados carregados antes da sidebar ─────────────────────────────────────────
# Carrega com ano padrão para ter ufs_disponiveis na sidebar
_ano_default = st.session_state.get("ano_sel", _anos[0])
_df_default  = carregar_dados(_ano_default)
_ufs_disp    = sorted(_df_default["uf"].unique().tolist())

# ── Callbacks ────────────────────────────────────────────────────────────────
def _on_regiao_change():
    """Callback do selectbox de região — preenche o multiselect de UFs.

    Disparado quando o usuário escolhe uma região; substitui a seleção
    atual do multiselect (`ms_ufs`) pelas UFs daquela região.
    """
    regiao = st.session_state.get("sel_regiao", "— nenhum —")
    st.session_state["ms_ufs"] = (
        [u for u in REGIOES.get(regiao, []) if u in _ufs_disp]
        if regiao != "— nenhum —" else []
    )

def _on_todos_change():
    """Callback do checkbox "Todos os estados" — limpa a seleção ao desmarcar.

    Ao desmarcar, esvazia o multiselect de UFs para o usuário escolher um
    subconjunto explicitamente (em vez de manter a seleção anterior).
    """
    if not st.session_state.get("chk_todos", True):
        st.session_state["ms_ufs"] = []

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.divider()

    ano_sel = st.selectbox("📅 Ano de referência", options=_anos, index=0, key="ano_sel")
    ano_ant = _anos[_anos.index(ano_sel) + 1] if _anos.index(ano_sel) + 1 < len(_anos) else None

    st.divider()
    st.markdown("**🗺️ Estados**")

    todos = st.checkbox("Todos os estados", value=True, key="chk_todos", on_change=_on_todos_change)

    if not todos:
        regiao_atual = st.session_state.get("sel_regiao", "— nenhum —")
        st.selectbox(
            "Filtrar por região:",
            options=["— nenhum —"] + list(REGIOES.keys()),
            key="sel_regiao",
            on_change=_on_regiao_change,
        )
        regiao_atual = st.session_state.get("sel_regiao", "— nenhum —")

        if regiao_atual != "— nenhum —":
            _ufs_regiao = [u for u in REGIOES.get(regiao_atual, []) if u in _ufs_disp]
            st.markdown(
                f"<div style='background:rgba(88,166,255,.1);border:1px solid rgba(88,166,255,.3);"
                f"border-radius:8px;padding:8px 12px;font-size:.82rem;color:#58a6ff;margin-top:4px'>"
                f"📍 <b>{regiao_atual}</b> · {len(_ufs_regiao)} estados</div>",
                unsafe_allow_html=True,
            )
            ufs_sel = _ufs_regiao
        else:
            ufs_sel = st.multiselect(
                "Estados:",
                options=_ufs_disp,
                key="ms_ufs",
                placeholder="Selecione estados...",
            )
            if not ufs_sel:
                ufs_sel = _ufs_disp
    else:
        ufs_sel = _ufs_disp

    st.divider()
    filtrar_idosos_pizza = False  # definido abaixo no card

# ── Tema ──────────────────────────────────────────────────────────────────────
t = THEMES[st.session_state.theme]
st.markdown(_css(t), unsafe_allow_html=True)

st.markdown("<style>iframe[height='50']{display:none!important;margin:0;padding:0;height:0!important}</style>", unsafe_allow_html=True)
inject_toggle()
if st.session_state.theme == "light":
    st.markdown("""
    <div class="cenarios-bar">
      <span class="cenarios-bar-logo">Cenários<span>+</span></span>
      <span class="cenarios-bar-sep">|</span>
      <span class="cenarios-bar-title">Dashboard Demográfico — Longevidade</span>
    </div>
    """, unsafe_allow_html=True)

# ── Dados ─────────────────────────────────────────────────────────────────────
df_raw             = carregar_dados(ano_sel)
df_proc, df_idosos = processar_dados(df_raw)
df_evo             = carregar_evolucao()

df_ant                     = carregar_dados(ano_ant) if ano_ant else None
df_proc_ant, df_idosos_ant = processar_dados(df_ant) if df_ant is not None else (None, None)

pop_total = int(df_proc["populacao"].sum())
n_ufs     = df_proc["uf"].nunique()

with st.sidebar:
    st.caption(f"📊 **{_fmt(pop_total)}** hab. · **{len(ufs_sel)}** de {n_ufs} estados · IBGE {ano_sel}")

# ── Métricas filtradas ────────────────────────────────────────────────────────
df_filt    = df_proc[df_proc["uf"].isin(ufs_sel)]
df_id_filt = df_idosos[df_idosos["uf"].isin(ufs_sel)]

pop_filt       = int(df_filt["populacao"].sum())
pct_fem_filt   = (df_filt[df_filt["sexo"] == "F"]["populacao"].sum() / pop_filt * 100) if pop_filt else 0
pct_idog_filt  = (df_filt[df_filt["idade"] >= 60]["populacao"].sum() / pop_filt * 100) if pop_filt else 0
idade_med_filt = ((df_filt["idade"] * df_filt["populacao"]).sum() / pop_filt) if pop_filt else 0

if df_proc_ant is not None:
    df_filt_ant  = df_proc_ant[df_proc_ant["uf"].isin(ufs_sel)]
    pop_ant      = int(df_filt_ant["populacao"].sum())
    pct_idog_ant = (df_filt_ant[df_filt_ant["idade"] >= 60]["populacao"].sum() / pop_ant * 100) if pop_ant else 0
    pct_fem_ant  = (df_filt_ant[df_filt_ant["sexo"] == "F"]["populacao"].sum() / pop_ant * 100) if pop_ant else 0
    idade_ant    = ((df_filt_ant["idade"] * df_filt_ant["populacao"]).sum() / pop_ant) if pop_ant else 0
else:
    pop_ant = pct_idog_ant = pct_fem_ant = idade_ant = 0

# ── Hero ──────────────────────────────────────────────────────────────────────
_label_ufs = (
    "Todos os estados" if len(ufs_sel) == n_ufs
    else f"{len(ufs_sel)} estado{'s' if len(ufs_sel) > 1 else ''} selecionado{'s' if len(ufs_sel) > 1 else ''}"
)

st.markdown(f"""
<div class="hero">
  <h1 class="hero-title">🗺️ Dashboard Demográfico — Longevidade</h1>
  <p class="hero-subtitle">
    Análise demográfica com distribuição etária, proporção de idosos,
    pirâmide populacional e evolução histórica por estado.
  </p>
  <div class="hero-badges">
    <span class="hero-badge accent"><span class="dot"></span>{_label_ufs}</span>
    <span class="hero-badge success"><span class="dot"></span>{_fmt(pop_filt)} pessoas</span>
    <span class="hero-badge"><span class="dot"></span>IBGE · {ano_sel}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── KPIs ──────────────────────────────────────────────────────────────────────
kpi_items = [
    ("👥", "População total",     _fmt(pop_filt),             f"{len(ufs_sel)} estado(s)",
     _delta_html(pop_filt, pop_ant),            "blue"),
    ("👴", "Proporção de idosos", f"{pct_idog_filt:.1f}%",    "≥ 60 anos",
     _delta_html(pct_idog_filt, pct_idog_ant),  "orange"),
    ("♀️", "Proporção feminina",  f"{pct_fem_filt:.1f}%",     "sobre o total",
     _delta_html(pct_fem_filt, pct_fem_ant),    "purple"),
    ("📅", "Idade média",         f"{idade_med_filt:.1f} anos","média ponderada",
     _delta_html(idade_med_filt, idade_ant),    "green"),
]

cols = st.columns(4)
for col, (icon, title, value, sub, delta, color) in zip(cols, kpi_items):
    with col:
        st.markdown(kpi_card(title, value, sub, icon, delta, color), unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)
st.divider()

# ── 01 · Mapa + 02 · Top 5 ───────────────────────────────────────────────────
col_mapa, col_top5 = st.columns([3, 2])

with col_mapa:
    st.markdown(section_header("01", "Proporção de Idosos por Estado",
        "Percentual da população com 60 anos ou mais em cada estado."), unsafe_allow_html=True)
    st.pydeck_chart(mapa.deck(df_id_filt, t), use_container_width=True)
    st.markdown(mapa.legenda(df_id_filt, t), unsafe_allow_html=True)

with col_top5:
    st.markdown(section_header("02", "Top estados — % de idosos",
        "Estados com maior proporção de pessoas com 60 anos ou mais."), unsafe_allow_html=True)
    top_n = min(15, len(df_id_filt))
    top15 = (
        df_id_filt[["uf", "pct_idosos", "idosos"]]
        .sort_values("pct_idosos", ascending=False).head(top_n)
        .rename(columns={"uf": "UF", "pct_idosos": "% Idosos", "idosos": "Idosos"})
        .reset_index(drop=True)
    )
    top15["% Idosos"] = top15["% Idosos"].map("{:.2f}%".format)
    top15["Idosos"]   = top15["Idosos"].map("{:,.0f}".format)
    st.markdown(html_top5(top15, t), unsafe_allow_html=True)

st.divider()

# ── 03 · Distribuição por Sexo + 04 · Pirâmide Etária ────────────────────────
col_pizza, col_piramide = st.columns([1, 1], gap="large")

with col_pizza:
    st.markdown(section_header("03", "Distribuição por Sexo"), unsafe_allow_html=True)
    filtrar_idosos_pizza = st.toggle("Apenas ≥ 60 anos", value=False)
    st.plotly_chart(fig_pizza(df_filt, t, filtrar_idosos_pizza), use_container_width=True, config=PLOTLY_CFG)

with col_piramide:
    st.markdown(section_header("04", "Pirâmide Etária",
        "Distribuição por faixa de 5 anos e sexo. Base larga = pop. jovem · Topo largo = pop. envelhecida."),
        unsafe_allow_html=True)
    st.plotly_chart(fig_piramide(df_filt, t), use_container_width=True, config=PLOTLY_CFG)

st.divider()

# ── 05 · Evolução + 06 · Ranking ─────────────────────────────────────────────
col_evo, col_rank = st.columns([1, 1], gap="large")

with col_evo:
    st.markdown(section_header("05", "Evolução Populacional — 2010 a 2025",
        "Total de habitantes nos estados selecionados ao longo dos anos."), unsafe_allow_html=True)
    st.plotly_chart(fig_evolucao(df_evo, ufs_sel, t), use_container_width=True, config=PLOTLY_CFG)

with col_rank:
    st.markdown(section_header("06", "Ranking — Proporção de Idosos por Estado",
        "Estados ordenados pela proporção de pessoas com 60+ anos."), unsafe_allow_html=True)
    st.plotly_chart(fig_ranking(df_id_filt, t), use_container_width=True, config=PLOTLY_CFG)

st.divider()

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="cenarios-footer" style="
    background:#2B7BB9;
    border-radius:12px;
    padding:28px 36px;
    margin-top:8px;
">
    <div style="font-size:1.2rem;font-weight:800;color:#ffffff;letter-spacing:-0.3px;margin-bottom:4px;">
        Cenários<span style="color:#E07B54">+</span>
    </div>
    <div style="font-size:.82rem;color:rgba(255,255,255,.75);">Todos os direitos reservados.</div>
</div>
""", unsafe_allow_html=True)
