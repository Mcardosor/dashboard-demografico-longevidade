# Conferência dos números com o IBGE

> **15/set/2026 — a base mudou.** O que está abaixo foi feito sobre a base
> municipal (2010-2025, idade até 80+). Em 15/set ela foi substituída pela
> tab1 do próprio IBGE (2000-2070, idade até 90+), conferida célula a célula
> contra a antiga: 8 células de 69.984 divergem, no máximo 66 pessoas. Com a
> troca, a diferença de 4 pessoas nos 60+ de 2025 virou zero, a idade média
> passou a bater no centésimo e a pirâmide ganhou as faixas 80-84 e 85-89.
> Os valores de referência estão presos em `tests/test_numeros.py`. Ver
> [Levantamento das projeções](levantamento-projecoes.md).

Feita em 04/set/2026. A pergunta era simples: os números que o painel mostra
são os do IBGE?

**São.** E a conferência achou um defeito que só apareceu porque ela foi feita.

## Contra o que foi conferido

O painel usa as **Projeções da População, revisão 2024** — a atual. Duas
fontes oficiais foram usadas:

| Fonte | Para quê |
|---|---|
| [Estimativas de População 2025 (Diário Oficial)](https://ftp.ibge.gov.br/Estimativas_de_Populacao/Estimativas_2025/estimativa_dou_2025.pdf) | Total por UF |
| [`projecoes_2024_tab1_idade_simples.xlsx`](https://ftp.ibge.gov.br/Projecao_da_Populacao/Projecao_da_Populacao_2024/) | População por idade simples, sexo e UF |

**Cuidado com a SIDRA.** A tabela 7358 ("População, por sexo e idade") ainda é
a **revisão 2018** e projeta 219.029.093 habitantes para 2025 — 5,6 milhões a
mais que a revisão atual. Conferir contra ela produziria um "erro" de 2,6% que
não é erro nosso, é revisão diferente. A revisão 2024 não está na SIDRA; só
nos arquivos do FTP.

## Resultado

| | IBGE | Painel | Diferença |
|---|---:|---:|---:|
| População 2010 | 194.749.329 | 194.749.329 | **0** |
| População 2025 | 213.421.037 | 213.421.037 | **0** |
| Pessoas 60+, 2010 | 20.718.042 | 20.718.042 | **0** |
| Pessoas 60+, 2025 | 35.370.902 | 35.370.898 | −4 |

As **27 UFs** foram comparadas uma a uma em 2025: divergência de zero pessoa
em todas.

A diferença de 4 pessoas em 35,4 milhões (0,00001%) está em três idades —
30, 31 e 33 anos — e é arredondamento na agregação de município para UF.

## O que a conferência revelou

**A base termina num balde aberto aos 80 anos.** A idade 80 não significa
"quem tem 80": é "80 anos ou mais", e guarda 4.956.207 pessoas em 2025.

Isso passou despercebido porque os totais fechavam. Duas consequências:

**A pirâmide mentia no rótulo.** Ela desenhava faixas até "100+". Com o balde
aos 80, aqueles 4,96 milhões caíam todos dentro de **"80-84"** — 1,8 vezes o
valor real da faixa, que é 2.713.413 — e as faixas 85-89, 90-94, 95-99 e 100+
apareciam **zeradas**, sugerindo que ninguém no Brasil passa dos 85 anos.

Corrigido: a última faixa passou a ser **"80+"**, que é o que o dado sustenta.
`test_ultima_faixa_da_piramide_e_aberta` e `test_nenhuma_faixa_fica_vazia`
impedem a volta.

**A idade média é subestimada em um décimo de ano.** Contar todo mundo de 80+
como tendo exatamente 80 puxa a média para baixo: 36,11 contra 36,21 do IBGE.
Pequeno, mas o número não deve ser tratado como exato.

O que **não** foi afetado: a contagem e a proporção de 60+, o índice de
envelhecimento e as classes do mapa. Todos dependem apenas do corte em 60, que
o balde aos 80 não atravessa.

## Como refazer

Não há teste automatizado desta conferência — ela depende de baixar planilha do
FTP do IBGE, o que não cabe numa suíte. O que ficou preso em `tests/` foi o que
ela revelou, em `test_numeros.py`.

Para refazer, compare a soma por UF e por idade contra a `tab1_idade_simples`
da revisão vigente. Se o IBGE publicar uma revisão nova, os dois arquivos em
`data/` precisam ser regerados juntos — e o teto de idade reconferido, porque é
ele que define as faixas da pirâmide.

## Pendência

A planilha do IBGE traz idade simples **até 90+**, contra os 80+ da nossa base.
Trocar a origem dos parquets por ela daria uma pirâmide com duas faixas a mais
(80-84, 85-89) e uma idade média mais fiel. Exige mexer no pipeline de dados,
que não está neste repositório — ver [Arquitetura](ARQUITETURA.md).
