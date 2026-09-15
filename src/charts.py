import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .data import ESTIMATIVA_ATE
from .utils import H_MEDIUM, H_LARGE, _apply_layout

#: Última idade da base, e balde aberto: 90 é "90 ou mais". A última faixa da
#: pirâmide é este número seguido de "+".
IDADE_TOPO = 90


def processar_dados(df: pd.DataFrame):
    """Deriva faixa etária e o recorte de idosos por UF a partir da base bruta.

    Args:
        df: DataFrame de um único ano, colunas `uf`, `idade`, `sexo`,
            `populacao` (ver `src.data.carregar_dados`).

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]:
            - `df_proc`: mesma base recebida, com a coluna `faixa_etaria`
              (bins de 5 em 5 anos, "90+" no topo) adicionada.
            - `df_idosos`: uma linha por UF, com `total`, `idosos` (idade
              >= 60) e `pct_idosos`.
    """
    # A última faixa é **90+**, porque a base termina em 90 e essa idade não é
    # "quem tem 90": é o balde aberto "90 anos ou mais" da tab1 do IBGE.
    #
    # A faixa final tem que coincidir com o balde da base. Quando a base
    # parava em 80 e a pirâmide desenhava até 100+, os 4,96 milhões de 80+
    # caíam inteiros em "80-84" — 1,8x o valor real — e quatro faixas acima
    # ficavam zeradas, sugerindo que ninguém no Brasil passa dos 85.
    # `IDADE_TOPO` em tests/test_numeros.py prende a coincidência.
    bins   = list(range(0, IDADE_TOPO + 1, 5)) + [200]
    labels = [f"{i}-{i+4}" for i in range(0, IDADE_TOPO, 5)] + [f"{IDADE_TOPO}+"]

    df_proc = df.copy()
    df_proc["faixa_etaria"] = pd.cut(df_proc["idade"], bins=bins, labels=labels, right=False)

    total_uf  = df_proc.groupby("uf")["populacao"].sum().rename("total")
    idosos_uf = (
        df_proc[df_proc["idade"] >= 60]
        .groupby("uf")["populacao"].sum()
        .rename("idosos")
    )
    df_idosos = pd.concat([total_uf, idosos_uf], axis=1).fillna(0).reset_index()
    df_idosos["pct_idosos"] = (df_idosos["idosos"] / df_idosos["total"] * 100).round(2)

    return df_proc, df_idosos


def fig_pizza(df: pd.DataFrame, t: dict, apenas_idosos: bool = False) -> go.Figure:
    """Monta o gráfico de rosca de distribuição por sexo.

    Args:
        df: base processada (ver `processar_dados`), colunas `idade`,
            `sexo`, `populacao`.
        t: dicionário de tema (cores) atual.
        apenas_idosos: quando True, restringe a base a idade >= 60 antes
            de agregar (toggle "Apenas ≥ 60 anos" da UI).

    Returns:
        go.Figure: gráfico de rosca com o total no centro.
    """
    from .utils import _fmt
    df_pie = df[df["idade"] >= 60].copy() if apenas_idosos else df.copy()
    agg = df_pie.groupby("sexo")["populacao"].sum().reset_index()
    agg["label"] = agg["sexo"].map({"M": "Masculino", "F": "Feminino"})
    total = agg["populacao"].sum()

    fig = px.pie(
        agg, names="label", values="populacao", color="label",
        color_discrete_map={"Masculino": t["serie_m"], "Feminino": t["serie_f"]},
        hole=0.55,
    )
    fig.update_traces(
        textposition="inside",
        texttemplate="%{percent:.1%}",
        textfont=dict(size=14, color="#ffffff"),
        insidetextorientation="horizontal",
        hovertemplate="<b>%{label}</b><br>%{value:,} pessoas<br>%{percent:.1%}<extra></extra>",
        marker_line_color=t["bg"],
        marker_line_width=3,
        pull=[0.03, 0.03],
    )
    _apply_layout(fig, t, H_MEDIUM)
    fig.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom", y=-0.08,
            xanchor="center", x=0.5,
            font=dict(size=13, color=t["text"]),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=20, r=20, t=20, b=20),
        annotations=[dict(
            text=f"<b>{_fmt(total)}</b><br><span style='font-size:11px'>{('pessoas com 60+' if apenas_idosos else 'pessoas')}</span>",
            x=0.5, y=0.5, font=dict(size=18, color=t["text_title"]),
            showarrow=False, align="center",
        )],
    )
    return fig


def fig_piramide(df: pd.DataFrame, t: dict) -> go.Figure:
    """Monta a pirâmide etária (barras horizontais opostas por sexo).

    Masculino é plotado como valores negativos (`x=-masc.values`) para
    ficar à esquerda do eixo zero, convenção padrão de pirâmide etária.

    Args:
        df: base processada (ver `processar_dados`), precisa da coluna
            `faixa_etaria`.
        t: dicionário de tema (cores) atual.

    Returns:
        go.Figure: pirâmide etária com barras opostas.
    """
    # Termina em "90+" porque a base termina ali — ver `processar_dados`.
    FAIXAS = [f"{i}-{i+4}" for i in range(0, IDADE_TOPO, 5)] + [f"{IDADE_TOPO}+"]
    agg = df.groupby(["faixa_etaria", "sexo"], observed=False)["populacao"].sum().reset_index()
    agg["faixa_etaria"] = agg["faixa_etaria"].astype(str)
    agg = agg[agg["faixa_etaria"].isin(FAIXAS)]

    masc = agg[agg["sexo"] == "M"].set_index("faixa_etaria")["populacao"].reindex(FAIXAS, fill_value=0)
    fem  = agg[agg["sexo"] == "F"].set_index("faixa_etaria")["populacao"].reindex(FAIXAS, fill_value=0)
    max_val   = max(masc.max(), fem.max())
    tick_step = max(1, int(max_val // 5))

    fig = go.Figure([
        go.Bar(
            y=FAIXAS, x=-masc.values, name="Masculino", orientation="h",
            marker_color=t["serie_m"], marker_line_color=t["bar_line"], marker_line_width=0.6,
            hovertemplate="<b>%{y}</b><br>Masculino: %{customdata:,}<extra></extra>",
            customdata=masc.values,
        ),
        go.Bar(
            y=FAIXAS, x=fem.values, name="Feminino", orientation="h",
            marker_color=t["serie_f"], marker_line_color=t["bar_line"], marker_line_width=0.6,
            hovertemplate="<b>%{y}</b><br>Feminino: %{x:,}<extra></extra>",
        ),
    ])
    _apply_layout(fig, t, H_LARGE)
    fig.update_layout(
        barmode="relative", bargap=0.08,
        xaxis=dict(
            title=dict(text="← Masculino  |  Feminino →", font=dict(color=t["text"])),
            tickmode="array",
            tickvals=list(range(-int(max_val * 1.1), int(max_val * 1.1) + 1, tick_step)),
            ticktext=[f"{abs(v):,}" for v in range(-int(max_val * 1.1), int(max_val * 1.1) + 1, tick_step)],
            range=[-max_val * 1.15, max_val * 1.15],
            zeroline=True, zerolinecolor=t["border"], zerolinewidth=2,
            tickfont=dict(color=t["text_muted"]),
        ),
        yaxis=dict(title="", tickfont=dict(size=10, color=t["text"])),
        showlegend=False,
        margin=dict(l=10, r=20, t=30, b=40),
    )
    return fig


def fig_evolucao(df_evo: pd.DataFrame, ufs: list, t: dict) -> go.Figure:
    """Monta a série de população total, 2000-2070, em milhões.

    Duas linhas com a mesma cor e continuidade: **sólida** até o último ano
    que o IBGE estima (`ESTIMATIVA_ATE`, 2022) e **tracejada** daí em
    diante, que é projeção. A fronteira é desenhada como faixa vertical
    rotulada, e não só pela textura da linha, porque tracejado sem legenda
    lê como estilo.

    A escala do eixo y não começa em zero, de propósito. Somando o país, a
    curva vai de 174 M (2000) a 220 M (2041) e volta a 199 M (2070) — o
    pico e a queda são a história, e num eixo desde o zero eles viram uma
    ondulação de 10% numa linha quase reta. Decisão documentada em
    docs/DOCUMENTACAO_GRAFICOS.md.

    Args:
        df_evo: população por UF e ano (ver `src.data.carregar_evolucao`).
        ufs: siglas das UFs selecionadas no filtro; a soma é recalculada
            sobre esse subconjunto a cada chamada.
        t: dicionário de tema (cores) atual.

    Returns:
        go.Figure: linha sólida (estimativa) + tracejada (projeção).
    """
    df_f   = df_evo[df_evo["uf"].isin(ufs)]
    df_tot = df_f.groupby("ano")["populacao"].sum().reset_index()
    df_tot["populacao_M"] = df_tot["populacao"] / 1_000_000

    # O ponto da fronteira entra nas duas séries, para a linha não ter buraco.
    # Mas o hover dele fica só na estimativa: com `hovermode="x unified"` o
    # ponto repetido aparecia duas vezes no tooltip de 2022, com o mesmo
    # número — dois dados onde há um.
    est  = df_tot[df_tot["ano"] <= ESTIMATIVA_ATE]
    proj = df_tot[df_tot["ano"] >= ESTIMATIVA_ATE]
    hover_proj = ["skip" if a == ESTIMATIVA_ATE else "all" for a in proj["ano"]]

    hover = "<b>%{x}</b><br>%{y:.2f}M habitantes<extra>%{fullData.name}</extra>"
    fig = go.Figure([
        go.Scatter(
            x=est["ano"], y=est["populacao_M"], name="Estimativa",
            mode="lines", line=dict(color=t["accent"], width=2.5),
            hovertemplate=hover,
        ),
        go.Scatter(
            x=proj["ano"], y=proj["populacao_M"], name="Projeção",
            mode="lines", line=dict(color=t["accent"], width=2.5, dash="dash"),
            hovertemplate=hover, hoverinfo=hover_proj,
        ),
    ])

    # O pico: onde a série vira. É o número que o gráfico existe para mostrar.
    #
    # A âncora do texto depende de onde o pico cai. Ele está sempre no topo
    # do gráfico — é o máximo —, e no topo também mora o rótulo da fronteira,
    # à direita de 2022. Um pico logo depois da fronteira (RS e AL em 2026,
    # RJ em 2027) punha os dois textos um sobre o outro; um pico em 2070 (MT)
    # ficava centrado na borda direita e era cortado pela margem.
    pico = df_tot.loc[df_tot["populacao_M"].idxmax()]
    ano_pico = int(pico["ano"])
    x_min, x_max = int(df_tot["ano"].min()), int(df_tot["ano"].max())
    perto_da_fronteira = ESTIMATIVA_ATE < ano_pico <= ESTIMATIVA_ATE + 10
    perto_da_borda = ano_pico >= x_max - 8
    if perto_da_fronteira or perto_da_borda:
        # Texto à esquerda do ponto, e descendo em vez de subindo, para sair
        # da faixa do topo onde está o rótulo da fronteira.
        xanchor, ax, ay = "right", -14, 28
    elif ano_pico <= x_min + 8:
        xanchor, ax, ay = "left", 14, 28
    else:
        xanchor, ax, ay = "center", 0, -32
    fig.add_annotation(
        x=ano_pico, y=pico["populacao_M"], xanchor=xanchor,
        text=f"pico em {ano_pico}: {pico['populacao_M']:.1f} M",
        showarrow=True, arrowhead=0, arrowcolor=t["text_muted"],
        ax=ax, ay=ay, font=dict(size=11, color=t["text"]),
    )

    fig.add_vline(
        x=ESTIMATIVA_ATE + 0.5, line_width=1, line_dash="dot", line_color=t["text_muted"],
    )
    fig.add_annotation(
        x=ESTIMATIVA_ATE + 0.5, y=1, yref="paper", yanchor="top", xanchor="left",
        text="  projeção do IBGE →", showarrow=False,
        font=dict(size=11, color=t["text_muted"]),
    )

    _apply_layout(fig, t, H_MEDIUM)
    fig.update_layout(
        xaxis=dict(title="", tickmode="linear", dtick=5, tickfont=dict(color=t["text_muted"])),
        yaxis=dict(
            title=dict(text="Milhões de habitantes", font=dict(color=t["text"])),
            tickfont=dict(color=t["text_muted"]),
        ),
        legend=dict(orientation="h", y=-0.15, x=0, font=dict(color=t["text"])),
        hovermode="x unified",
        # r=36: o rótulo "2070" do último tick cabe; com 10 ele era cortado.
        margin=dict(l=10, r=36, t=20, b=10),
    )
    return fig
