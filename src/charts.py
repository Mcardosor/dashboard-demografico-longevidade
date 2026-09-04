import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .utils import H_MEDIUM, H_LARGE, _apply_layout


def processar_dados(df: pd.DataFrame):
    """Deriva faixa etária e o recorte de idosos por UF a partir da base bruta.

    Args:
        df: DataFrame de um único ano, colunas `uf`, `idade`, `sexo`,
            `populacao` (ver `src.data.carregar_dados`).

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]:
            - `df_proc`: mesma base recebida, com a coluna `faixa_etaria`
              (bins de 5 em 5 anos, "100+" no topo) adicionada.
            - `df_idosos`: uma linha por UF, com `total`, `idosos` (idade
              >= 60) e `pct_idosos`.
    """
    # A última faixa é **80+**, e não 80-84 seguida de 85-89, 90-94, 95-99 e
    # 100+.
    #
    # A base termina em 80, e essa idade não é "quem tem 80": é o balde aberto
    # "80 anos ou mais", com 4,96 milhões de pessoas em 2025. Conferido contra
    # a planilha de idade simples da revisão 2024 do IBGE.
    #
    # Com as faixas antigas a pirâmide desenhava esses 4,96 milhões dentro de
    # "80-84" — 1,8x o valor real da faixa, que é 2,71 milhões — e deixava
    # 85-89, 90-94, 95-99 e 100+ zeradas, dando a entender que ninguém no
    # Brasil passa dos 85. Os rótulos afirmavam o que o dado não sustenta.
    bins   = list(range(0, 81, 5)) + [200]
    labels = [f"{i}-{i+4}" for i in range(0, 80, 5)] + ["80+"]

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
    # Termina em "80+" porque a base termina ali — ver `processar_dados`.
    FAIXAS = [
        "0-4","5-9","10-14","15-19","20-24","25-29","30-34","35-39",
        "40-44","45-49","50-54","55-59","60-64","65-69","70-74","75-79",
        "80+",
    ]
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
    """Monta a série histórica de população total (2010-2025) em milhões.

    Args:
        df_evo: população por UF e ano (ver `src.data.carregar_evolucao`).
        ufs: siglas das UFs selecionadas no filtro; a soma é recalculada
            sobre esse subconjunto a cada chamada.
        t: dicionário de tema (cores) atual.

    Returns:
        go.Figure: gráfico de linha com marcadores, um ponto por ano.
    """
    df_f  = df_evo[df_evo["uf"].isin(ufs)].copy()
    df_tot = df_f.groupby("ano")["populacao"].sum().reset_index()
    df_tot["populacao_M"] = df_tot["populacao"] / 1_000_000

    fig = px.line(
        df_tot, x="ano", y="populacao_M",
        labels={"ano": "Ano", "populacao_M": "População (milhões)"},
        markers=True,
        color_discrete_sequence=[t["accent"]],
    )
    fig.update_traces(
        line_width=2.5,
        marker=dict(size=7, color=t["accent"]),
        hovertemplate="<b>%{x}</b><br>%{y:.2f}M habitantes<extra></extra>",
    )
    from .utils import H_MEDIUM
    _apply_layout(fig, t, H_MEDIUM)
    fig.update_layout(
        xaxis=dict(title="", tickmode="linear", dtick=1, tickfont=dict(color=t["text_muted"])),
        yaxis=dict(title=dict(text="Milhões de habitantes", font=dict(color=t["text"])), tickfont=dict(color=t["text_muted"])),
        margin=dict(l=10, r=10, t=20, b=10),
    )
    return fig
