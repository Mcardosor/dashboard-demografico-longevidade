"""Gera os parquets de `data/` a partir das planilhas do IBGE.

Roda uma vez, sempre que o IBGE publicar uma revisão nova. O painel em
execução não lê planilha nenhuma — lê o que este script escreve.

    python scripts/preparar_projecao.py <pasta com as planilhas da revisão>

A pasta é a do FTP do IBGE (`Projecao_da_Populacao/Projecao_da_Populacao_2024/`),
baixada inteira. O script usa duas das cinco planilhas:

| Planilha | Vira | O que carrega |
|---|---|---|
| `projecoes_2024_tab1_idade_simples.xlsx` | `data/pop_uf.parquet` | população por UF × ano × sexo × idade simples |
| `projecoes_2024_tab4_indicadores.xlsx` | `data/indicadores_uf.parquet` | esperança de vida ao nascer e aos 60, por sexo |

**Por que a tab1 e não a base municipal que havia antes.** O painel nunca
usou município: todo gráfico soma por UF antes de desenhar. A base municipal
tinha 14,4 milhões de linhas e 23 MB para produzir os mesmos números que a
tab1 produz com 350 mil linhas — e a tab1 ainda vai de 2000 a 2070 e conta a
idade até 90+, contra 2010-2025 e 80+. A conferência que fundamenta a troca
está em docs/levantamento-projecoes.md.

Três cuidados que a planilha exige, e que este script cumpre:

- **Filtrar `CÓD. >= 11`.** As planilhas trazem Brasil (0) e Grandes Regiões
  (1-5) nas mesmas linhas das UFs. Sem o filtro, cada total sai dobrado.
- **`data_only=True`.** O cabeçalho de anos da tab1 é fórmula (`=F6+1`);
  sem isso o openpyxl devolve o texto da fórmula em vez do número.
- **Descartar "Ambos".** É a soma de Homens e Mulheres; manter as três
  linhas dobraria a população em qualquer `groupby` por sexo.
"""

from __future__ import annotations

import os
import sys

import openpyxl
import pandas as pd

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

#: Primeiro código de UF nas planilhas. Abaixo dele são Brasil e regiões.
COD_PRIMEIRA_UF = 11

#: Colunas da tab4 que o painel usa: esperança de vida ao nascer (e0) e aos
#: 60 anos (e60), ambos os sexos (_T), homens (_H) e mulheres (_M).
COLUNAS_INDICADORES = ["e0_T", "e0_H", "e0_M", "e60_T", "e60_H", "e60_M"]

SEXO = {"Homens": "M", "Mulheres": "F"}


def _abrir(caminho: str) -> openpyxl.worksheet._read_only.ReadOnlyWorksheet:
    wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    return wb.worksheets[0]


def ler_tab1(caminho: str) -> pd.DataFrame:
    """População por UF × ano × sexo × idade simples, formato longo.

    Na planilha os anos são colunas (F em diante) e cada linha é uma
    idade × sexo × local. Aqui vira uma linha por (uf, ano, sexo, idade).
    """
    ws = _abrir(caminho)
    linhas = ws.iter_rows(min_row=6, values_only=True)
    cabecalho = next(linhas)
    anos = [int(v) for v in cabecalho[5:] if v is not None]

    registros = []
    for r in linhas:
        idade, sexo, cod, sigla = r[0], r[1], r[2], r[3]
        if idade is None or cod < COD_PRIMEIRA_UF or sexo not in SEXO:
            continue
        for ano, valor in zip(anos, r[5:]):
            registros.append((sigla, ano, SEXO[sexo], int(idade), int(valor)))

    df = pd.DataFrame(registros, columns=["uf", "ano", "sexo", "idade", "populacao"])
    return df.astype({"ano": "int16", "idade": "int8", "populacao": "int64"})


def ler_tab4(caminho: str) -> pd.DataFrame:
    """Esperança de vida por UF × ano, ao nascer e aos 60, por sexo."""
    ws = _abrir(caminho)
    linhas = ws.iter_rows(min_row=7, values_only=True)
    cabecalho = list(next(linhas))
    idx = {nome: cabecalho.index(nome) for nome in ["ANO", "SIGLA", *COLUNAS_INDICADORES]}
    # A coluna de código tem acento no nome e o encoding do console varia;
    # ela é a segunda, sempre.
    idx_cod = 1

    registros = [
        (r[idx["SIGLA"]], int(r[idx["ANO"]]), *[float(r[idx[c]]) for c in COLUNAS_INDICADORES])
        for r in linhas
        if r[0] is not None and r[idx_cod] >= COD_PRIMEIRA_UF
    ]
    df = pd.DataFrame(registros, columns=["uf", "ano", *COLUNAS_INDICADORES])
    return df.astype({"ano": "int16"})


def main(pasta: str) -> None:
    tab1 = os.path.join(pasta, "projecoes_2024_tab1_idade_simples.xlsx")
    tab4 = os.path.join(pasta, "projecoes_2024_tab4_indicadores.xlsx")

    pop = ler_tab1(tab1)
    assert pop["uf"].nunique() == 27, pop["uf"].nunique()
    assert pop.duplicated(["uf", "ano", "sexo", "idade"]).sum() == 0
    destino = os.path.join(_DATA_DIR, "pop_uf.parquet")
    pop.to_parquet(destino, index=False, compression="zstd")
    print(f"{destino}: {len(pop):,} linhas, {pop.ano.min()}-{pop.ano.max()}, "
          f"idade {pop.idade.min()}-{pop.idade.max()}, {os.path.getsize(destino) / 1024:.0f} KB")

    ind = ler_tab4(tab4)
    assert ind["uf"].nunique() == 27, ind["uf"].nunique()
    assert ind.duplicated(["uf", "ano"]).sum() == 0
    destino = os.path.join(_DATA_DIR, "indicadores_uf.parquet")
    ind.to_parquet(destino, index=False, compression="zstd")
    print(f"{destino}: {len(ind):,} linhas, {os.path.getsize(destino) / 1024:.0f} KB")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
