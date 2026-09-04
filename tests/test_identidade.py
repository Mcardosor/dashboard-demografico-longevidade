"""A identidade visual da Plataforma da Longevidade.

As cores não são escolha de gosto: saíram do CSS do longevidade.unb.br e
passaram pelo validador do skill `dataviz`. Estes testes prendem o que a
validação garantiu, para que um ajuste "no olho" não desfaça em silêncio.

Ver docs/identidade.md para os números e o porquê de cada escolha.
"""

from __future__ import annotations

import pytest

from src.themes import ROXO_MARCA, THEMES, marca_html

#: Primária do site do Observatório, lida do CSS dele (`--primary`).
PRIMARIA_DO_SITE = "#6B2F96"

#: A flor do logo, amostrada do JPEG oficial.
MAGENTA_DA_FLOR = "#AA2DA3"


def test_roxo_da_marca_e_o_do_site():
    assert ROXO_MARCA == PRIMARIA_DO_SITE
    assert THEMES["light"]["accent"] == PRIMARIA_DO_SITE
    assert THEMES["light"]["accent2"] == MAGENTA_DA_FLOR


@pytest.mark.parametrize("modo", ["light", "dark"])
def test_serie_m_e_f_nao_sao_dois_roxos(modo):
    """O par óbvio — roxo da marca + magenta da flor — reprova.

    Medido: ΔE 5,3 em protanopia e **12,7 até com visão normal de cor**,
    abaixo do piso de 15. As duas metades da pirâmide etária ficariam
    indistinguíveis. O par que passa nos dois temas é roxo + terracota.

    A guarda aqui é grosseira de propósito: exige que as duas séries fiquem
    em famílias de matiz distantes. Quem quiser trocar de par que rode o
    validador de novo.
    """
    t = THEMES[modo]
    m, f = t["serie_m"], t["serie_f"]
    assert m != f

    def matiz(hexa: str) -> float:
        import colorsys
        h = hexa.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        return colorsys.rgb_to_hsv(r, g, b)[0] * 360

    distancia = abs(matiz(m) - matiz(f))
    distancia = min(distancia, 360 - distancia)
    assert distancia > 60, f"{m} e {f} estão a {distancia:.0f}° — perto demais"


def test_wordmark_traz_a_flor_no_lugar_do_o():
    html = marca_html("Dashboard Demográfico")
    assert "Plataforma" in html
    assert "L<svg" in html and "ngevidade" in html, "a flor ocupa o lugar do 'o'"
    assert "Dashboard Demográfico" in html


def test_wordmark_sem_titulo_omite_o_separador():
    html = marca_html()
    assert "marca-bar-sep" not in html
    assert "ngevidade" in html


def test_nao_sobrou_marca_do_cenarios():
    """O painel deixou de ser Cenários+; o CSS e o markup não podem ter ficado
    com a marca antiga pendurada."""
    from src.themes import _css

    for modo, t in THEMES.items():
        css = _css(t)
        assert "cenarios-bar" not in css, modo
        assert "#2B7BB9" not in css, f"azul do Cenários em {modo}"
        assert "#E07B54" not in css, f"terracota do Cenários em {modo}"
