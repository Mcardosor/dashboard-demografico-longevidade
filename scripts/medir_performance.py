"""Linha de base de performance do painel demográfico.

Mede duas coisas diferentes, que costumam ser confundidas:

1. **Tempo de servidor** — quanto custa ler os parquets e montar cada figura,
   sem o cache do Streamlit, para saber o custo real por operação.
2. **Payload** — quantos bytes cada figura despacha para o navegador. No
   coroplético isso importa mais do que o tempo: a geometria vai *embutida*
   no JSON da figura e volta pela rede a cada rerun.

O painel do sinan aprendeu na marca que medir só o item 1 esconde o gargalo
(ver `paineis/sinan/docs/performance.md`). Aqui os dois saem juntos.

Uso::

    python -m scripts.medir_performance
"""

from __future__ import annotations

import json
import statistics
import time
from collections.abc import Callable

import plotly.io as pio

from src import charts, data, mapa
from src.themes import THEMES

REPETICOES = 5

#: Tema usado nas figuras. A cor não muda o custo, mas fixa a medição.
TEMA = THEMES["light"]

#: Recortes de UF, do mais pesado para o mais leve. O filtro de estados é o
#: que o usuário mais mexe, então o custo precisa ser conhecido nos extremos.
RECORTES = {
    "BR (27 UFs)": None,
    "Sudeste (4)": ["ES", "MG", "RJ", "SP"],
    "PE (1)": ["PE"],
}


def _sem_cache(fn: Callable) -> Callable:
    """Devolve a função por baixo do decorador de cache do Streamlit.

    `st.cache_data` e `st.cache_resource` usam `functools.wraps`, então a
    original fica em `__wrapped__`. Medir por cima do cache mediria o
    dicionário de cache, não o trabalho.
    """
    return getattr(fn, "__wrapped__", fn)


def cronometrar(fn: Callable[[], object]) -> tuple[float, float]:
    """Devolve (mediana, pior) em milissegundos, descartando a primeira chamada."""
    fn()  # aquece metadados do parquet / alocações do pandas
    tempos = []
    for _ in range(REPETICOES):
        inicio = time.perf_counter()
        fn()
        tempos.append((time.perf_counter() - inicio) * 1000)
    return statistics.median(tempos), max(tempos)


def _payload_kb(fig) -> float:
    """Tamanho, em KB, do JSON que o Streamlit despacha para o navegador.

    O `pydeck.Deck` traz o seu `to_json`; as figuras do Plotly passam pelo
    `plotly.io`. Os dois medem a mesma coisa: os bytes que saem do servidor.
    """
    if hasattr(fig, "to_json") and not hasattr(fig, "update_layout"):
        return len(fig.to_json().encode("utf-8")) / 1024
    return len(pio.to_json(fig).encode("utf-8")) / 1024


def main() -> None:
    ano = _sem_cache(data.anos_disponiveis)()[0]
    geojson = _sem_cache(data.carregar_geojson)()
    df_raw = _sem_cache(data.carregar_dados)(ano)
    df_evo = _sem_cache(data.carregar_evolucao)()
    df_proc, df_idosos = charts.processar_dados(df_raw)

    print(f"Ano de referência: {ano} · mediana de {REPETICOES} execuções, "
          f"em ms (primeira descartada)\n")

    # ── Camada de dados ──────────────────────────────────────────────────────
    print("── Camada de dados (sem cache) ──")
    leituras: dict[str, Callable[[], object]] = {
        "carregar_geojson": lambda: _sem_cache(data.carregar_geojson)(),
        "_carregar_base": lambda: _sem_cache(data._carregar_base)(),
        "carregar_dados(ano)": lambda: _sem_cache(data.carregar_dados)(ano),
        "carregar_evolucao": lambda: _sem_cache(data.carregar_evolucao)(),
        "processar_dados": lambda: charts.processar_dados(df_raw),
    }
    largura = 24
    print(f"{'operação':<{largura}}{'mediana':>12}{'pior':>10}")
    for nome, fn in leituras.items():
        mediana, pior = cronometrar(fn)
        print(f"{nome:<{largura}}{mediana:>12.1f}{pior:>10.1f}")

    # ── Figuras, por recorte ─────────────────────────────────────────────────
    print("\n── Figuras: tempo de montagem (ms) e payload (KB) ──")
    cabecalho = f"{'figura':<{largura}}"
    for rotulo in RECORTES:
        cabecalho += f"{rotulo:>22}"
    print(cabecalho)

    for nome in ("mapa.deck", "fig_pizza", "fig_piramide", "fig_evolucao"):
        linha = f"{nome:<{largura}}"
        for ufs in RECORTES.values():
            df_f = df_proc if ufs is None else df_proc[df_proc["uf"].isin(ufs)]
            df_i = df_idosos if ufs is None else df_idosos[df_idosos["uf"].isin(ufs)]
            ufs_ev = sorted(df_idosos["uf"]) if ufs is None else ufs

            # Os `=df_f` e afins amarram o valor desta volta do laço. Sem
            # isso as lambdas leriam a variável no momento da chamada — aqui
            # daria certo por acaso, porque a chamada é imediata, mas é o
            # tipo de acaso que quebra quando alguém move a linha.
            construtores = {
                "mapa.deck": lambda d=df_i: mapa.deck(d, TEMA),
                "fig_pizza": lambda d=df_f: charts.fig_pizza(d, TEMA),
                "fig_piramide": lambda d=df_f: charts.fig_piramide(d, TEMA),
                "fig_evolucao": lambda u=ufs_ev: charts.fig_evolucao(df_evo, u, TEMA),
            }
            construir = construtores[nome]
            mediana, _ = cronometrar(construir)
            linha += f"{mediana:>13.1f}{_payload_kb(construir()):>9.0f}"
        print(linha)

    print("\n(cada célula: mediana em ms / payload em KB)")

    # ── O arquivo em disco, para comparar com o payload ──────────────────────
    bruto = len(json.dumps(geojson).encode("utf-8")) / 1024
    print(f"\nGeoJSON serializado sem indentação: {bruto:,.0f} KB")


if __name__ == "__main__":
    main()
