import plotly.graph_objects as go

PLOTLY_CFG = {"displayModeBar": True, "scrollZoom": False}
H_SMALL, H_MEDIUM, H_LARGE = 320, 420, 680
# As cores de série mudaram de lugar: vivem em `themes.THEMES[modo]`, porque
# cada tema tem o seu par validado. Ver docs/identidade.md — o par "roxo da
# marca + magenta da flor", que era o óbvio, reprova em daltonismo E em visão
# normal de cor.

REGIOES = {
    "Norte":     ["AC","AM","AP","PA","RO","RR","TO"],
    "Nordeste":  ["AL","BA","CE","MA","PB","PE","PI","RN","SE"],
    "Centro-Oeste": ["DF","GO","MS","MT"],
    "Sudeste":   ["ES","MG","RJ","SP"],
    "Sul":       ["PR","RS","SC"],
}


def _fmt(n: float) -> str:
    """Formata um número grande de forma compacta (1.2M, 340.5K, 87).

    Args:
        n: valor numérico a formatar.

    Returns:
        str: número formatado com sufixo M/K quando aplicável.
    """
    if abs(n) >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if abs(n) >= 1_000:
        return f"{n/1_000:.1f}K"
    return f"{n:.0f}"


def _delta_html(val: float, prev: float, invert: bool = False) -> str:
    """Monta o HTML do indicador de variação (▲/▼ X% vs ano anterior).

    Args:
        val: valor do período atual.
        prev: valor do período anterior; se 0, não há comparação possível.
        invert: quando True, inverte a semântica de cor (útil para métricas
            onde "subir" é ruim, ex: mortalidade).

    Returns:
        str: HTML pronto para `unsafe_allow_html`, ou string vazia se não
            houver valor anterior para comparar.
    """
    if prev == 0:
        return ""
    diff = val - prev
    pct  = diff / prev * 100
    arrow = "▲" if diff >= 0 else "▼"
    cls = "kpi-delta-pos" if (diff >= 0) != invert else "kpi-delta-neg"
    if diff == 0:
        cls = "kpi-delta-neu"
    return f'<span class="{cls}">{arrow} {abs(pct):.1f}% vs ano anterior</span>'


def kpi_card(title: str, value: str, subtitle: str, icon: str,
             delta_html: str = "", color: str = "blue") -> str:
    """Monta o HTML de um card de KPI (título, valor, subtítulo e variação).

    Args:
        title: rótulo do indicador (ex: "População total").
        value: valor já formatado para exibição (ex: "12.3M").
        subtitle: texto pequeno abaixo do valor.
        icon: emoji exibido no canto do card.
        delta_html: HTML da variação vs. período anterior (ver `_delta_html`),
            omitido do card se vazio.
        color: nome da cor de destaque (classe CSS `.kpi-card.{color}`).

    Returns:
        str: HTML pronto para `unsafe_allow_html`.
    """
    return f"""
    <div class="kpi-card {color}">
      <div class="kpi-header">
        <div class="kpi-title">{title}</div>
        <div class="kpi-icon">{icon}</div>
      </div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-sub">{subtitle}</div>
      {f'<div style="margin-top:4px">{delta_html}</div>' if delta_html else ''}
    </div>"""


def section_header(num: str, title: str, caption: str = "") -> str:
    """Monta o cabeçalho numerado de cada seção do dashboard (ex: "01 · Mapa").

    Args:
        num: número da seção, como string com dois dígitos (ex: "01").
        title: título da seção.
        caption: legenda opcional exibida abaixo do título.

    Returns:
        str: HTML pronto para `unsafe_allow_html`.
    """
    cap = f'<p class="section-caption">{caption}</p>' if caption else ""
    return f"""
    <div class="section-header">
      <span class="section-num">{num}</span>
      <h3 class="section-title">{title}</h3>
    </div>
    {cap}"""


def html_top5(df, t: dict) -> str:
    """Monta a tabela HTML do ranking Top 5/15 de estados por % de idosos.

    Args:
        df: DataFrame já ordenado e formatado, com colunas `UF`,
            `% Idosos` e `Idosos` (strings prontas para exibição).
        t: dicionário de tema (cores) atual, ver `src.themes.THEMES`.

    Returns:
        str: HTML da tabela, pronto para `unsafe_allow_html`.
    """
    rows = ""
    medals = [f"{i}º" for i in range(1, len(df) + 1)]
    for i, (_, row) in enumerate(df.iterrows()):
        rows += f"""
        <tr style="border-bottom:1px solid {t['border']}">
          <td style="padding:8px 10px;color:{t['text_muted']};font-size:.8rem">{medals[i]}</td>
          <td style="padding:8px 10px;font-weight:700;color:{t['accent']}">{row['UF']}</td>
          <td style="padding:8px 10px;text-align:right;font-weight:600;color:{t['text_title']}">{row['% Idosos']}</td>
          <td style="padding:8px 10px;text-align:right;color:{t['text_muted']};font-size:.8rem">{row['Idosos']}</td>
        </tr>"""
    return f"""
    <table style="width:100%;border-collapse:collapse;font-size:.85rem;
                  background:{t['bg_card']};border-radius:10px;overflow:hidden;
                  border:1px solid {t['border']}">
      <thead>
        <tr style="background:{t['bg']};border-bottom:2px solid {t['border']}">
          <th style="padding:8px 10px;text-align:left;color:{t['text_muted']};font-size:.72rem;text-transform:uppercase;letter-spacing:.05em">#</th>
          <th style="padding:8px 10px;text-align:left;color:{t['text_muted']};font-size:.72rem;text-transform:uppercase;letter-spacing:.05em">UF</th>
          <th style="padding:8px 10px;text-align:right;color:{t['text_muted']};font-size:.72rem;text-transform:uppercase;letter-spacing:.05em">% Idosos</th>
          <th style="padding:8px 10px;text-align:right;color:{t['text_muted']};font-size:.72rem;text-transform:uppercase;letter-spacing:.05em">Total Idosos</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""


def _apply_layout(fig: go.Figure, t: dict, height: int = H_MEDIUM) -> go.Figure:
    """Aplica o tema (cores, grade, legenda) e a altura padrão a uma figura Plotly.

    Centraliza o estilo visual comum entre os gráficos para evitar repetir
    a mesma configuração de eixos/legenda em cada função `fig_*`.

    Args:
        fig: figura Plotly já construída (traces já adicionados).
        t: dicionário de tema (cores) atual, ver `src.themes.THEMES`.
        height: altura em pixels do gráfico.

    Returns:
        go.Figure: a mesma figura recebida, com o layout aplicado.
    """
    fig.update_layout(
        height=height,
        paper_bgcolor=t["bg_plot"],
        plot_bgcolor=t["bg_plot"],
        font=dict(color=t["text"], size=12),
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(
            bgcolor=t["bg_card"], bordercolor=t["border"], borderwidth=1,
            font=dict(color=t["text"]),
        ),
    )
    fig.update_xaxes(
        gridcolor=t["grid"], linecolor=t["border"], zerolinecolor=t["border"],
        tickfont=dict(color=t["text_muted"]),
        title_font=dict(color=t["text"]),
    )
    fig.update_yaxes(
        gridcolor=t["grid"], linecolor=t["border"], zerolinecolor=t["border"],
        tickfont=dict(color=t["text_muted"]),
        title_font=dict(color=t["text"]),
    )
    return fig
