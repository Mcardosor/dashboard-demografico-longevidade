"""Tema, CSS e a marca do painel."""

#: A flor de cinco pétalas do logo da Plataforma da Longevidade, que no
#: original ocupa o lugar do "o" de "Longevidade".
#:
#: Refeita em SVG, e não recortada do JPEG oficial (823x247, fundo branco):
#: assim escala sem serrilhar, funciona no tema escuro — onde uma caixa branca
#: ficaria evidente — e as pétalas herdam a cor do texto via `currentColor`.
#:
#: O `{miolo}` é a cor do centro, que precisa casar com o fundo atrás da flor.
FLOR_SVG = """<svg class="marca-flor" viewBox="0 0 100 100" aria-hidden="true">
        <g fill="currentColor">
          <ellipse cx="50" cy="25" rx="19" ry="24"/>
          <ellipse cx="50" cy="25" rx="19" ry="24" transform="rotate(72 50 50)"/>
          <ellipse cx="50" cy="25" rx="19" ry="24" transform="rotate(144 50 50)"/>
          <ellipse cx="50" cy="25" rx="19" ry="24" transform="rotate(216 50 50)"/>
          <ellipse cx="50" cy="25" rx="19" ry="24" transform="rotate(288 50 50)"/>
        </g>
        <circle cx="50" cy="50" r="15" fill="{miolo}"/>
      </svg>"""

#: Roxo da barra e do rodapé — a primária do longevidade.unb.br.
ROXO_MARCA = "#6B2F96"


def marca_html(titulo: str = "") -> str:
    """Wordmark da Plataforma da Longevidade, pronto para `unsafe_allow_html`.

    Args:
        titulo: texto do lado direito, após o separador. Vazio omite os dois.
    """
    flor = FLOR_SVG.format(miolo=ROXO_MARCA)
    marca = (
        '<span class="marca-bar-logo">'
        '<span class="marca-bar-pre">Plataforma</span>'
        f'L{flor}ngevidade</span>'
    )
    if not titulo:
        return marca
    return (
        f'{marca}<span class="marca-bar-sep">|</span>'
        f'<span class="marca-bar-title">{titulo}</span>'
    )


THEMES = {
    "dark": {
        "bg":          "#0d1117",
        "bg_card":     "rgba(22,27,34,.92)",
        "bg_plot":     "rgba(0,0,0,0)",
        "text":        "#c9d1d9",
        "text_title":  "#f0f6fc",
        "text_muted":  "#8b949e",
        "border":      "#30363d",
        "border_hero": "#21262d",
        "grid":        "#21262d",
        "accent":      "#A177C7",
        "success":     "#7ee787",
        "danger":      "#f85149",
        "hero_bg":     "linear-gradient(135deg,#1b1425 0%,#0d1117 60%,#241436 100%)",
        "map_line":    "#30363d",
        "bar_line":    "#0d1117",
        "footer":      "#484f58",
        "sidebar_bg":  "#010409",
        "toggle_icon": "☀️",
        "toggle_label":"Modo claro",
        # Série categórica e rampa do mapa: degraus **próprios** do tema
        # escuro, não o espelho do claro. Ver docs/identidade.md.
        "serie_m":     "#9E79CC",
        "serie_f":     "#EA630E",
        "rampa":       ("#E0CDF2", "#C6ACE0", "#AE8AD2",
                        "#9668C4", "#7F4DB8", "#6B3F9E"),
    },
    "light": {
        "bg":          "#f6f8fa",
        "bg_card":     "rgba(255,255,255,.98)",
        "bg_plot":     "rgba(0,0,0,0)",
        "text":        "#24292f",
        "text_title":  "#3D1A5C",
        "text_muted":  "#57606a",
        "border":      "#d0d7de",
        "border_hero": "#E4DAF0",
        "grid":        "#eaecef",
        "accent":      "#6B2F96",
        "accent2":     "#AA2DA3",
        "success":     "#1a7f37",
        "danger":      "#cf222e",
        "hero_bg":     "linear-gradient(135deg,#ffffff 0%,#F5F0FA 60%,#E9DCF6 100%)",
        "map_line":    "#d0d7de",
        "bar_line":    "#f6f8fa",
        "footer":      "#8c959f",
        "sidebar_bg":  "#ffffff",
        "toggle_icon": "🌙",
        "toggle_label":"Modo escuro",
        "serie_m":     "#7F4DB8",
        "serie_f":     "#C0663C",
        "rampa":       ("#BFA1DB", "#A177C7", "#8A4BBF",
                        "#6B2F96", "#552578", "#3D1A5C"),
    },
}


def _css(t: dict) -> str:
    """Monta o CSS global do app (hero, KPI cards, tabs, sidebar, widgets nativos).

    Args:
        t: dicionário de tema (`THEMES["light"]` ou `THEMES["dark"]`).

    Returns:
        str: tag `<style>` completa, pronta para `st.markdown(..., unsafe_allow_html=True)`.
    """
    return f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

  html, body, [class*="css"] {{
    font-family: 'Inter', 'Segoe UI', sans-serif;
  }}

  .stApp {{ background: {t['bg']}; color: {t['text']}; }}

  /* ── Sidebar ── */
  section[data-testid="stSidebar"] > div:first-child {{
    background: {t['sidebar_bg']};
    border-right: 1px solid {t['border']};
  }}

  /* ── Hero ── */
  .hero {{
    background: {t['hero_bg']};
    border: 1px solid {t['border_hero']};
    border-radius: 16px;
    padding: 36px 40px 30px;
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
  }}
  .hero::before {{
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    /* Fita da marca: magenta da flor -> roxo primário -> roxo escuro. Era o
       terracota/azul/verde do Cenários. */
    background: linear-gradient(90deg, #AA2DA3 0%, #6B2F96 50%, #3D1A5C 100%);
  }}
  .hero-title {{
    font-size: 2.1rem; font-weight: 800; color: {t['text_title']};
    display: flex; align-items: center; gap: 14px; margin: 0 0 10px;
    letter-spacing: -0.5px;
  }}
  .hero-subtitle {{
    color: {t['text_muted']}; font-size: .95rem;
    max-width: 680px; margin: 0 0 20px; line-height: 1.6;
  }}
  .hero-badges {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .hero-badge {{
    background: rgba(128,128,128,.08);
    border: 1px solid {t['border']};
    border-radius: 20px; padding: 5px 14px; font-size: .78rem;
    color: {t['text_muted']}; display: flex; align-items: center; gap: 6px;
    font-weight: 500;
  }}
  .hero-badge.accent {{
    background: {t['accent']}15;
    border-color: {t['accent']}50; color: {t['accent']};
  }}
  .hero-badge.success {{
    background: {t['success']}15;
    border-color: {t['success']}50; color: {t['success']};
  }}
  .dot {{ width: 7px; height: 7px; border-radius: 50%; background: currentColor; display: inline-block; }}

  /* ── KPI Cards ── */
  .kpi-grid {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; margin-bottom: 8px; }}
  .kpi-card {{
    background: {t['bg_card']};
    border: 1px solid {t['border']};
    border-top: 3px solid {t['accent']};
    border-radius: 12px;
    padding: 20px 22px 16px;
    transition: transform .15s, box-shadow .15s;
  }}
  .kpi-card:hover {{
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,.15);
  }}
  .kpi-card.green  {{ border-top-color: {t['success']}; }}
  .kpi-card.blue   {{ border-top-color: {t['accent']}; }}
  .kpi-card.purple {{ border-top-color: #bc8cff; }}
  .kpi-card.orange {{ border-top-color: #e3b341; }}

  .kpi-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }}
  .kpi-icon   {{ font-size: 1.5rem; }}
  .kpi-title  {{
    color: {t['text_muted']}; font-size: .72rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: .06em;
  }}
  .kpi-value  {{
    color: {t['text_title']}; font-size: 2.2rem; font-weight: 800;
    line-height: 1.1; margin: 2px 0 6px; letter-spacing: -1px;
  }}
  .kpi-sub    {{ color: {t['text_muted']}; font-size: .78rem; margin-bottom: 4px; }}
  .kpi-delta-pos {{ color: {t['success']}; font-size: .75rem; font-weight: 600; }}
  .kpi-delta-neg {{ color: {t['danger']};  font-size: .75rem; font-weight: 600; }}
  .kpi-delta-neu {{ color: {t['text_muted']}; font-size: .75rem; }}

  /* ── Section headers ── */
  .section-header {{
    display: flex; align-items: center; gap: 10px;
    margin: 8px 0 4px;
  }}
  .section-num {{
    background: {t['accent']}20;
    color: {t['accent']};
    font-size: .7rem; font-weight: 700;
    padding: 2px 8px; border-radius: 20px;
    border: 1px solid {t['accent']}40;
  }}
  .section-title {{
    font-size: 1.1rem; font-weight: 700;
    color: {t['text_title']}; margin: 0;
  }}
  .section-caption {{
    color: {t['text_muted']}; font-size: .82rem;
    margin: 0 0 12px; line-height: 1.5;
  }}

  /* ── Barra da marca (tema claro apenas) ── */
  .marca-bar {{
    background: #6B2F96;
    padding: 8px 24px;
    margin: 0.5rem -1rem 1.5rem -1rem;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  /* O wordmark: "Plataforma" leve por cima, "Longevidade" pesado embaixo,
     com a flor no lugar do "o" — como no logo oficial. Peso 800 e fonte de
     sistema acompanham o longevidade.unb.br, que não carrega webfont. */
  .marca-bar-logo {{
    display: flex;
    align-items: center;
    gap: 1px;
    font-size: 1.15rem;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.4px;
    line-height: 1;
  }}
  .marca-bar-pre {{
    font-size: .62rem;
    font-weight: 400;
    letter-spacing: .06em;
    color: rgba(255,255,255,.72);
    align-self: flex-start;
    margin-right: 7px;
    padding-top: 1px;
  }}
  /* A flor ocupa o lugar da letra, então acompanha a altura do texto. */
  .marca-flor {{
    width: .78em;
    height: .78em;
    margin: 0 .02em;
    position: relative;
    top: .04em;
  }}
  .marca-bar-sep {{
    color: rgba(255,255,255,.35);
    margin: 0 10px;
  }}
  .marca-bar-title {{
    font-size: .85rem;
    font-weight: 500;
    color: rgba(255,255,255,.85);
  }}

  /* ── Misc ── */
  h2, h3 {{ color: {t['text_title']} !important; }}
  hr {{ border-color: {t['grid']} !important; margin: 24px 0 !important; }}
  .stDataFrame {{ border-color: {t['border']} !important; border-radius: 8px !important; }}

  /* ── Widgets nativos do Streamlit ── */

  /* Botões */
  .stButton > button {{
    background-color: transparent !important;
    color: {t['text']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    width: 100%;
  }}
  .stButton > button p,
  .stButton > button span,
  .stButton > button div {{
    color: {t['text']} !important;
  }}
  .stButton > button:hover {{
    background-color: {t['accent']}18 !important;
    border-color: {t['accent']} !important;
    color: {t['accent']} !important;
  }}
  .stButton > button:hover p,
  .stButton > button:hover span {{
    color: {t['accent']} !important;
  }}

  /* Selectbox */
  [data-testid="stSelectbox"] > div > div {{
    background-color: {t['bg_card']} !important;
    border-color: {t['border']} !important;
    color: {t['text']} !important;
  }}
  [data-testid="stSelectbox"] label,
  [data-testid="stSelectbox"] span {{
    color: {t['text_muted']} !important;
  }}

  /* Multiselect */
  [data-testid="stMultiSelect"] > div > div {{
    background-color: {t['bg_card']} !important;
    border-color: {t['border']} !important;
  }}
  [data-testid="stMultiSelect"] label {{
    color: {t['text_muted']} !important;
  }}

  /* Checkbox e Toggle */
  .stCheckbox label, .stCheckbox p, .stCheckbox span,
  .stToggle label, .stToggle p, .stToggle span,
  [data-testid="stCheckbox"] label,
  [data-testid="stCheckbox"] p,
  [data-testid="stToggle"] label,
  [data-testid="stToggle"] p,
  [data-testid="stToggle"] > label > div > p,
  [data-testid="stToggle"] > label > div,
  div[class*="toggle"] p,
  div[class*="checkbox"] p {{
    color: {t['text']} !important;
    opacity: 1 !important;
  }}

  /* Divider */
  [data-testid="stDivider"] hr {{
    border-color: {t['border']} !important;
  }}

  /* Caption / texto pequeno */
  [data-testid="stCaptionContainer"] p {{
    color: {t['text_muted']} !important;
  }}

  /* Sidebar labels */
  section[data-testid="stSidebar"] label,
  section[data-testid="stSidebar"] p,
  section[data-testid="stSidebar"] span {{
    color: {t['text']} !important;
  }}

  /* Input text dropdown */
  [data-baseweb="select"] * {{
    background-color: {t['bg_card']} !important;
    color: {t['text']} !important;
  }}
  [data-baseweb="popover"] * {{
    background-color: {t['bg_card']} !important;
    color: {t['text']} !important;
  }}
  [data-baseweb="menu"] li:hover {{
    background-color: {t['accent']}20 !important;
  }}

  /* Esconde deploy button nativo */
  .stDeployButton {{ display: none !important; }}

  /* ── Tabs pill ── */
  .stTabs {{ margin-top: 1rem; }}
  .stTabs [data-baseweb="tab-list"] {{
    gap: 4px; background: rgba(0,0,0,.02); padding: 6px;
    border-radius: 12px; border: 1px solid {t['border']};
    flex-wrap: wrap !important; overflow-x: auto;
  }}
  .stTabs [data-baseweb="tab"] {{
    padding: 8px 14px !important; border-radius: 8px !important;
    font-weight: 600 !important; font-size: 13px !important;
    color: {t['text_muted']};
    white-space: nowrap; flex: 1 1 auto !important;
    text-align: center !important; cursor: pointer !important;
    border: 1px solid transparent !important;
  }}
  .stTabs [data-baseweb="tab"]:hover {{
    background: rgba(0,0,0,.04) !important;
    border-color: {t['border']} !important;
    color: {t['text']} !important;
  }}
  .stTabs [aria-selected="true"] {{
    background: rgba(224,123,84,.1) !important;
    border-color: rgba(224,123,84,.3) !important;
    color: {t['text_title']} !important;
    box-shadow: 0 2px 8px rgba(224,123,84,.1) !important;
  }}
  .stTabs [data-baseweb="tab-panel"] {{ padding-top: 1.25rem; }}
</style>
"""


# ── Dark CSS overrides (para JS toggle) ──────────────────────────────────────
_DARK_CSS = """
  [data-theme="dark"] [data-testid="stAppViewContainer"],
  [data-theme="dark"] [data-testid="stMain"],
  [data-theme="dark"] .block-container { background-color: #0d1117 !important; }
  [data-theme="dark"] [data-testid="stSidebar"] > div:first-child { background: #010409 !important; border-right: 1px solid #30363d !important; }
  [data-theme="dark"] [data-testid="stSidebar"] * { color: #c9d1d9 !important; }
  [data-theme="dark"] [data-testid="stHeader"] { background: #0d1117 !important; }
  [data-theme="dark"] h1, [data-theme="dark"] h2, [data-theme="dark"] h3 { color: #f0f6fc !important; }
  [data-theme="dark"] p, [data-theme="dark"] span, [data-theme="dark"] label { color: #c9d1d9 !important; }
  [data-theme="dark"] [data-testid="stCaption"] { color: #8b949e !important; }
  [data-theme="dark"] hr { background: linear-gradient(90deg,transparent,#30363d,transparent) !important; }
  [data-theme=dark] .kpi-card { background: rgba(22,27,34,.92) !important; border-left-color: #30363d !important; border-right-color: #30363d !important; border-bottom-color: #30363d !important; }
  [data-theme=dark] .kpi-value { color: #f0f6fc !important; }
  [data-theme=dark] .kpi-title { color: #8b949e !important; }
  [data-theme=dark] .kpi-sub   { color: #8b949e !important; }
  [data-theme="dark"] .hero { background: linear-gradient(135deg,#161b22 0%,#0d1117 60%,#0d2137 100%) !important; border-color: #21262d !important; }
  [data-theme=dark] .hero-title { color: #f0f6fc !important; }
  [data-theme=dark] .hero-subtitle a, [data-theme=dark] .hero-subtitle a:visited { color: #c9d1d9 !important; text-decoration: none !important; }
  [data-theme=dark] .hero p a, [data-theme=dark] .hero span a { color: #c9d1d9 !important; text-decoration: none !important; }
  [data-theme="dark"] .hero-subtitle, [data-theme="dark"] .hero-badge { color: #8b949e !important; border-color: #30363d !important; background: rgba(255,255,255,.04) !important; }
  [data-theme="dark"] .stTabs [data-baseweb="tab-list"] { background: rgba(255,255,255,.03) !important; border-color: #30363d !important; }
  [data-theme="dark"] .stTabs [data-baseweb="tab"] { color: #8b949e !important; }
  [data-theme="dark"] .stTabs [aria-selected="true"] { background: rgba(224,123,84,.12) !important; border-color: rgba(224,123,84,.3) !important; color: #f0f6fc !important; }
  [data-theme="dark"] [data-testid="stExpander"] { background: #161b22 !important; border-color: #30363d !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .bg { fill: #161b22 !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .g-gtitle text,
  [data-theme="dark"] .js-plotly-plot .plotly .xtick text,
  [data-theme="dark"] .js-plotly-plot .plotly .ytick text { fill: #8b949e !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .gridlayer path { stroke: #21262d !important; }
  [data-theme="dark"] #_tb_theme_btn { background: rgba(22,27,34,.9) !important; border-color: #30363d !important; color: #e6edf3 !important; }
"""

_THEME_TOGGLE_JS = """
<script>
(function() {
  var KEY = 'demografico_dash_theme';
  var p = window.parent;

  function applyTheme(t) {
    p.document.documentElement.setAttribute('data-theme', t);
    p.localStorage.setItem(KEY, t);
    var btn = p.document.getElementById('_tb_theme_btn');
    if (btn) btn.innerHTML = t === 'dark' ? '☀️' : '🌙';
    if (btn) btn.title = t === 'dark' ? 'Modo claro' : 'Modo escuro';
  }

  function toggle() {
    var cur = p.document.documentElement.getAttribute('data-theme') || 'light';
    var next = cur === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    // Clica o botão Streamlit da sidebar para re-renderizar gráficos
    var sidebarBtns = p.document.querySelectorAll('[data-testid="stSidebar"] button');
    if (sidebarBtns.length > 0) { sidebarBtns[0].click(); }
  }

  function ensureStyle() {
    if (p.document.getElementById('_demo_dark_css')) return;
    var s = p.document.createElement('style');
    s.id = '_demo_dark_css';
    s.textContent = DARK_CSS_PLACEHOLDER;
    p.document.head.appendChild(s);
  }

  function ensureButton() {
    if (p.document.getElementById('_tb_theme_btn')) return;
    var btn = p.document.createElement('button');
    btn.id = '_tb_theme_btn';
    btn.onclick = toggle;
    var saved = p.localStorage.getItem(KEY) || 'light';
    btn.innerHTML = saved === 'dark' ? '☀️' : '🌙';
    btn.title = saved === 'dark' ? 'Modo claro' : 'Modo escuro';
    btn.style.cssText = [
      'position:fixed','top:8px','z-index:9999999',
      'width:32px','height:32px','border-radius:8px',
      'border:1px solid rgba(0,0,0,.15)','background:rgba(255,255,255,.92)',
      'backdrop-filter:blur(8px)','cursor:pointer',
      'font-size:18px','line-height:1','padding:0',
      'box-shadow:0 1px 4px rgba(0,0,0,.15)',
      'transition:transform .12s,background .2s',
      'display:flex','align-items:center','justify-content:center'
    ].join(';');
    function _pos() {
      var vw = p.document.documentElement.clientWidth || p.innerWidth;
      btn.style.left = Math.max(0, vw - 122) + 'px';
    }
    _pos();
    p.addEventListener('resize', _pos);
    btn.onmouseover = function() { btn.style.transform = 'scale(1.1)'; };
    btn.onmouseout  = function() { btn.style.transform = 'scale(1)'; };
    p.document.body.appendChild(btn);
  }

  function init() {
    ensureStyle();
    var saved = p.localStorage.getItem(KEY) || 'light';
    applyTheme(saved);
    ensureButton();
  }

  if (p.document.readyState === 'complete') { init(); }
  else { p.addEventListener('load', init); }

  var obs = new p.MutationObserver(function() { ensureButton(); });
  obs.observe(p.document.body, { childList: true });

  // Evitar auto-scroll do Streamlit que empurra a marca-bar para cima
  setTimeout(function() { p.scrollTo(0, 0); }, 300);
})();
</script>

  /* ── Footer dark mode ─── */
  [data-theme="dark"] .marca-footer {
    background: #1b1425 !important;
    border-top: 1px solid #30363d !important;
  }
"""


def inject_toggle() -> None:
    """Injeta floating button lua/sol via iframe — identico ao TB SINAN e TB Recife."""
    import streamlit.components.v1 as components
    dark_css_escaped = _DARK_CSS.replace('\n', ' ').replace("'", "\'").replace('"', '\\"')
    js = _THEME_TOGGLE_JS.replace('DARK_CSS_PLACEHOLDER', f"'{dark_css_escaped}'")
    components.html(js, height=50, scrolling=False)
