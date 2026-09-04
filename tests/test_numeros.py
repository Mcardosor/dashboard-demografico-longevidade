"""Os números que o painel mostra batem com a fonte?

Conferido em 04/set/2026 contra as Projeções da População do IBGE, revisão
2024 (`projecoes_2024_tab1_idade_simples.xlsx`) e contra as Estimativas de
População 2025 publicadas no Diário Oficial:

- população total, 2010 e 2025: **idêntica**, e nas 27 UFs também
- pessoas com 60+: idêntica em 2010; 4 pessoas de diferença em 35,4 milhões
  em 2025, arredondamento na agregação

Estes testes não refazem aquela conferência — ela depende de baixar planilha
do IBGE e não cabe em suíte automatizada. Prendem o que ela **revelou**: que
a base termina num balde aberto aos 80 anos, e que a pirâmide precisa dizer
isso em vez de fingir faixas que não existem.
"""

from __future__ import annotations

import pandas as pd

from src.charts import processar_dados
from src.data import _carregar_base

#: Última idade da base. Não é "quem tem 80 anos": é "80 ou mais".
IDADE_TOPO = 80


def _base_2025() -> pd.DataFrame:
    b = _carregar_base.__wrapped__()
    return b[b["ano"] == 2025]


def test_base_termina_num_balde_aberto_aos_80():
    """Se um dia a base passar a trazer idades acima de 80, este teste falha —
    e aí a pirâmide pode voltar a ter faixas até 100+."""
    b = _carregar_base.__wrapped__()
    assert int(b["idade"].max()) == IDADE_TOPO


def test_ultima_faixa_da_piramide_e_aberta():
    """O defeito que a conferência com o IBGE achou.

    Com faixas até 100+, os 4,96 milhões de pessoas com 80 ou mais caíam todos
    em "80-84" — 1,8x o valor real da faixa — e 85-89, 90-94, 95-99 e 100+
    ficavam zeradas, sugerindo que ninguém no Brasil passa dos 85.
    """
    proc, _ = processar_dados(_base_2025())
    faixas = [str(f) for f in proc["faixa_etaria"].cat.categories]
    assert faixas[-1] == "80+"
    assert "85-89" not in faixas and "100+" not in faixas


def test_nenhuma_faixa_fica_vazia():
    """Faixa desenhada e sempre zerada é rótulo que promete dado inexistente."""
    proc, _ = processar_dados(_base_2025())
    soma = proc.groupby("faixa_etaria", observed=False)["populacao"].sum()
    vazias = [str(f) for f, v in soma.items() if v == 0]
    assert not vazias, f"faixas sempre vazias: {vazias}"


def test_faixas_somam_a_populacao():
    """Nenhuma pessoa se perde no corte das faixas."""
    base = _base_2025()
    proc, _ = processar_dados(base)
    soma = proc.groupby("faixa_etaria", observed=False)["populacao"].sum().sum()
    assert int(soma) == int(base["populacao"].sum())


def test_idade_media_e_subestimada_e_isso_esta_documentado():
    """Contar todo mundo de 80+ como tendo exatamente 80 puxa a média para
    baixo. Medido contra o IBGE: 36,11 contra 36,21 anos em 2025 — um décimo
    de ano. Fica registrado para ninguém tratar o número como exato."""
    base = _base_2025()
    media = (base["idade"] * base["populacao"]).sum() / base["populacao"].sum()
    assert 36.0 < media < 36.2
