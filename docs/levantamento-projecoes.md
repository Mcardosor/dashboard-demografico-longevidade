# Levantamento — Projeções da População (IBGE, revisão 2024)

> **Decisão (15/set/2026): a tab1 virou a base do painel.** Não uma camada
> colada na evolução — a fonte de tudo. O que está abaixo é o levantamento
> que fundamentou isso; o que foi feito está no commit que o acompanha, e o
> resultado em [Arquitetura](ARQUITETURA.md) e
> [Documentação dos gráficos](DOCUMENTACAO_GRAFICOS.md).
>
> Das decisões pendentes listadas no fim: o eixo é 2000-2070 inteiro, com a
> fronteira marcada; a escala não começa em zero; o `e60` substituiu a
> "Idade média" nos KPIs; e os quartis do mapa passaram a ser fixos sobre
> 2000-2070 (alternativas medidas na documentação dos gráficos).

Feito em 15/set/2026, antes de qualquer código. A pergunta: o que há nos
arquivos do IBGE, o que serve ao painel, e onde a emenda com o dado atual
pode dar errado.

Arquivos em `C:\Users\Cenarios-Matheus\Desktop\IBGE\PROJECAO_DA_POPULACAO_2024\`
(fora do repositório, como o pipeline dos parquets — ver [Arquitetura](ARQUITETURA.md)).

## A descoberta que muda o desenho

**A base atual do painel já é projeção em parte.** O IBGE divide a série da
revisão 2024 assim (relatório metodológico, cap. 1):

| Período | O que é |
|---|---|
| 2000 – 2022 | **Estimativas** — retropolação ancorada nos Censos 2000, 2010 e 2022, conciliadas por UF |
| 2023 – 2070 | **Projeções** — método das componentes demográficas com hipóteses de fecundidade, mortalidade e migração |

O `pop_ibge.parquet` vai de 2010 a 2025 e **bate com a tab1 ano a ano**: 432
pares UF×ano comparados, totais do Brasil idênticos em todos os 16 anos,
divergência máxima de 67 pessoas numa UF (arredondamento de município para
UF). Ou seja: o parquet não é "dado observado" — é o recorte 2010-2025 da
mesma série, e **2023, 2024 e 2025 já são projeção** nele.

Consequência para o gráfico: a fronteira observado/projetado **não é 2025**,
é **2022/2023**. Desenhar a linha sólida até 2025 e tracejada depois seria
apresentar três anos de projeção como se fossem contagem. O honesto é:
sólido até 2022, tracejado de 2023 em diante — e o Censo 2022 é a âncora que
justifica o corte ali.

A boa notícia da mesma conferência: **a emenda não tem degrau.** Como é a
mesma série, a curva projetada continua a atual sem salto em 2025.

## O que cada arquivo tem

Todos: Brasil, 5 Grandes Regiões e 27 UFs; 2000 a 2070, ano a ano. Os
códigos 0-5 são Brasil e regiões; **filtrar `CÓD. >= 11`** para ficar só com
as UFs, senão os totais dobram. Nenhum arquivo tem município.

| Arquivo | Grão | Linhas | Serve para |
|---|---|---:|---|
| `tab1_idade_simples` | idade 0-**90+** × sexo × UF, anos em colunas | 9.009 | pirâmide projetada; 60+ por ano; **substituir a origem do parquet** (o balde aberto aos 80 vira 90+) |
| `tab2_grupo_quinquenal` | faixas de 5 anos × sexo × UF | 1.887 | o mesmo, já agregado |
| `tab3_grupos_etarios_especificos` | totais e recortes prontos (0-14, 15-59, 60+, 65+, 80+…) por sexo × UF | 2.350 | 60+ projetado sem somar idades |
| `tab4_indicadores` | 60 indicadores por UF × ano | 2.350 | **esperança de vida, índice de envelhecimento, idade mediana — prontos** |
| `tab5_tabuas_mortalidade` | funções da tábua (nMx, nqx, lx, Lx, Tx, **ex**) por faixa × sexo × UF × ano | 140.585 | só se quiser `ex` numa idade que a tab4 não traz |

## Esperança de vida: não precisa calcular

A ideia era derivar a expectativa de vida das tábuas (tab5). **Não é
preciso.** A `tab4_indicadores` já traz, por UF, ano e sexo:

- `e0_T / e0_H / e0_M` — esperança de vida ao nascer
- `e60_T / e60_H / e60_M` — esperança de vida **aos 60 anos**

Conferido: o `e0` da tab4 é o `ex` da idade 0 na tab5, ao décimo de milésimo
(BR, mulheres, 2000: 75,0766 nos dois). A tab5 tem 24 MB para dar o mesmo
número; fica de fora.

Para um painel sobre 60+, **o `e60` é o indicador mais pertinente**: quantos
anos, em média, ainda vive quem chegou aos 60. Ele fala do público do painel;
o `e0` fala de recém-nascidos.

O que os números dizem (ambos os sexos):

| Ano | e0 (mín – máx) | e60 | Índice de envelhecimento | Idade mediana |
|---|---|---|---|---|
| 2010 | 71,8 (AL) – 76,5 (DF) | 20,6 – 22,5 | 15 – 63 | 22,1 – 32,6 |
| 2025 | 74,6 (AP) – 79,9 (DF) | 21,6 – 24,5 | 30 – 121 | 27,7 – 38,7 |
| 2050 | 80,2 – 82,9 | 24,6 – 26,1 | 119 – 255 | 38,6 – 47,7 |
| 2070 | 83,4 – 84,6 | 26,3 – 27,0 | 203 – 368 | 44,8 – 53,3 |

A dispersão entre UFs **encolhe** com o tempo (5,3 anos de e0 em 2025, 1,2 em
2070): a hipótese do IBGE é de convergência. Vale dizer isso no painel, senão
o leitor lê o achatamento das linhas como dado e não como hipótese.

A diferença homens/mulheres em 2025 é de 6 a 8 anos em toda UF (AP: 70,5
contra 79,0). É a variável com mais contraste do conjunto.

## O que a projeção da população diz

Brasil (tab1, soma das 27 UFs):

| 2025 | 2030 | **2041 (pico)** | 2050 | 2060 | 2070 |
|---:|---:|---:|---:|---:|---:|
| 213,4 M | 217,0 M | **220,4 M** | 218,4 M | 211,1 M | 199,2 M |

**O país começa a encolher em 2042**, e chega a 2070 com menos gente que em
2025. Isso o gráfico de evolução atual não tem como mostrar — ele para em
2025, no meio da subida.

E cada UF tem o seu ano de virada:

| Já em 2026-2027 | Década de 2030 | 2040-2049 | Só depois de 2050 |
|---|---|---|---|
| **AL, RS** (2026), **RJ** (2027) | MA, BA, PI, SP, MG, PE, RN | RO, SE, CE, DF, AC, PB, PR, AP, ES, PA, TO | MS, AM, GO, SC, RR, **MT (ainda cresce em 2070)** |

RS e AL atingem o pico **no ano que vem**. É a manchete que a camada de
projeção entrega — e não aparece em nenhum outro lugar do painel.

## Riscos e decisões pendentes

1. **Rótulo da fronteira.** Sólido/tracejado em 2022/2023, não em 2025 (ver
   acima). Precisa de uma nota curta no gráfico: "estimativa até 2022; projeção
   do IBGE de 2023 em diante".
2. **Filtro de recorte.** O gráfico de evolução soma as UFs selecionadas. A
   projeção acompanha isso sem esforço: mesma chave `uf`×`ano`.
3. **Quanto mostrar.** 2010-2070 são 61 anos; o trecho atual (16) vira um
   quarto do eixo. Alternativas: eixo inteiro com a fronteira marcada, ou um
   controle "até 2025 / até 2070". Decisão de leitura, não de dado.
4. **Escala.** Com todas as UFs somadas a projeção quase não muda de nível
   (213 → 220 → 199 M). A história está na **forma** (pico e queda), e uma
   escala que não começa em zero é o que a torna visível. Decidir e
   documentar.
5. **Peso do arquivo.** Só o que o gráfico usa: `uf`, `ano`, `populacao`
   (27 × 71 = 1.917 linhas, alguns KB em parquet). Os indicadores da tab4
   idem (2.350 linhas). Não embarcar as planilhas.
6. **Trocar a origem do parquet pela tab1** resolve de vez a pendência da
   pirâmide (80+ → 90+) e da idade média — mas é o pipeline fora do repo.
   Fica registrado, não entra neste passo.

## Como refazer a conferência

Os dois recortes que serviram a este levantamento estão em parquet no
scratchpad da sessão (`proj_uf_ano.parquet`, `indicadores_uf.parquet`). São
descartáveis: o passo seguinte gera os definitivos em `data/`, com script.

Leitura das planilhas: `openpyxl` em `read_only=True, data_only=True` — o
cabeçalho de anos da tab1 é fórmula (`=F6+1`), e sem `data_only` vem o texto
da fórmula em vez do número.
