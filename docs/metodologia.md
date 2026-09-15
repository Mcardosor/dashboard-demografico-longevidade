# Metodologia — de onde vem cada número do painel

Esta página é a referência. Ela responde, para cada número que aparece na
tela, três perguntas: **de onde vem, como é calculado e o que ele não diz**.
O histórico de como se chegou a cada decisão fica nos outros documentos,
apontados ao longo do texto; aqui está só o que vale hoje.

Os valores citados como exemplo são os do painel aberto em **2026, todos os
estados**, salvo indicação. Os de referência estão presos em
`tests/test_numeros.py` — se um parquet regerado os mudar, o CI acusa.

## 1. A fonte

**Projeções da População: Brasil e Unidades da Federação, revisão 2024**,
do IBGE — Diretoria de Pesquisas, Coordenação de População e Indicadores
Sociais. É a projeção oficial vigente, ancorada no Censo Demográfico 2022.

| O que | Onde |
|---|---|
| Planilhas | [ftp.ibge.gov.br/Projecao_da_Populacao/Projecao_da_Populacao_2024/](https://ftp.ibge.gov.br/Projecao_da_Populacao/Projecao_da_Populacao_2024/) |
| Metodologia do IBGE | *Série Relatórios Metodológicos*, v. 40, 3ª ed. (na mesma pasta) |
| Duas planilhas usadas | `tab1_idade_simples` (população) e `tab4_indicadores` (esperança de vida) |

O painel não lê as planilhas: lê dois parquets em `data/`, gerados por
`scripts/preparar_projecao.py`. O script filtra as 27 UFs (as planilhas
trazem Brasil e Grandes Regiões nas mesmas linhas), descarta as linhas
"Ambos os sexos" (soma de Homens e Mulheres) e grava:

| Arquivo | Grão | Linhas |
|---|---|---:|
| `pop_uf.parquet` | UF × ano × sexo × idade simples (0 a 90+) | 348.894 |
| `indicadores_uf.parquet` | UF × ano: `e0` e `e60`, por sexo e total | 1.917 |

**Não há município.** O IBGE não projeta população municipal; o que existe
por município são as Estimativas anuais (Diário Oficial, para o FPM), só do
ano corrente. Todo número deste painel é por UF ou soma de UFs.

**Cuidado com a SIDRA.** A tabela 7358 ("População, por sexo e idade") ainda
é a **revisão 2018** e dá 219,0 milhões para 2025 — 5,6 milhões acima da
revisão atual. Conferir o painel contra ela produz um "erro" que não é
nosso.

## 2. Estimativa e projeção

O IBGE divide a série em duas partes, e o painel repete a divisão:

| Anos | O que é | Como aparece no painel |
|---|---|---|
| **2000 – 2022** | **Estimativas**: retropolação ancorada nos Censos 2000, 2010 e 2022, conciliadas por UF | linha sólida; ano sem marca |
| **2023 – 2070** | **Projeções**: método das componentes demográficas, com hipóteses de fecundidade, mortalidade e migração | linha tracejada; "· projeção" no seletor e no hero |

A fronteira é `ESTIMATIVA_ATE = 2022` em `src/data.py`. **O ano em que o
painel abre — o corrente — é projeção**, e o painel diz isso. Não é
contagem: é o que o modelo do IBGE espera para o ano, dadas as hipóteses.

Uma revisão nova do IBGE muda os números projetados. O painel mostra a
revisão vigente e não guarda a anterior.

## 3. Os quatro indicadores do topo

Calculados em `app.py::_indicadores()` sobre o **recorte** — todos os
estados, uma região, uma lista de estados, ou o estado em foco no mapa — e
o **ano** escolhidos. "vs ano anterior" compara com o mesmo recorte no ano
imediatamente anterior da base; em 2000 não há comparação.

### Pessoas com 60+

Soma da população de idade **≥ 60** no recorte e no ano. 2026: 36.570.129.

O painel fala "60+" e "pessoas com 60 anos ou mais", nunca "idosos" — ver o
[vocabulário](DOCUMENTACAO_GRAFICOS.md#vocabulário).

### Proporção de 60+

    pessoas com 60+ ÷ população total × 100

2026: 36.570.129 ÷ 214.211.951 = **17,07%**.

### Índice de envelhecimento

    pessoas com 60+ ÷ pessoas de 0 a 14 anos × 100

Quantas pessoas de 60+ existem para cada 100 crianças. É o indicador
clássico da transição demográfica e o que mais se move no período: 43 em
2010, 85 em 2025, **89 em 2026**, 220 em 2050.

**Corte em 60, não em 65.** O IBGE publica as duas versões (`IE60` e `IE65`
na tab4); o painel usa 60 porque é o corte de todo o resto — 60+ é a
definição legal de pessoa idosa no Brasil (Estatuto da Pessoa Idosa, Lei
10.741/2003). Comparações com fontes que usam 65+ (OMS, OCDE) vão dar
números menores; não é discrepância, é definição.

### Esperança de vida aos 60 (e60)

Quantos anos, em média, ainda vive quem chegou aos 60. **É o valor oficial
do IBGE** (`e60_T` na tab4, derivado das tábuas de mortalidade da própria
revisão), não uma conta do painel. 2026: 21,7 anos em AL, 24,5 no DF.

O IBGE publica o `e60` por UF e para o Brasil — não para um conjunto
qualquer de estados. Para um recorte, o painel faz a **média das UFs
ponderada pela população de 60+** de cada uma, que é a população a que o
indicador se refere:

    e60(recorte) = Σ e60(uf) × pop60(uf) ÷ Σ pop60(uf)

Conferido contra o valor oficial do Brasil: 22,71 contra 22,73 em 2025, e
diferença abaixo de 0,01 ano em 2010, 2050 e 2070 (`test_e60_do_pais_bate_com_o_oficial`).
Para um estado só, é o valor oficial sem ponderar.

**Por que aos 60 e não ao nascer.** O `e0` (esperança de vida ao nascer)
fala de recém-nascidos e é dominado pela mortalidade infantil. Num painel
sobre 60+, o número que fala do público é o `e60`.

## 4. O mapa: onde estão os 60+

Cada UF é pintada pela **proporção de 60+** dela no ano, em quatro classes.

**Os cortes são fixos**, calculados uma vez sobre **todas as UFs e todos os
anos, 2000 a 2070**, como quartis da distribuição inteira:

| Classe | Proporção de 60+ |
|---|---|
| 1 (mais clara) | até 11,45% |
| 2 | 11,45 a 19,74% |
| 3 | 19,74 a 29,94% |
| 4 (mais escura) | 29,94% ou mais |

Fixos porque o mapa existe para mostrar o envelhecimento **ao longo do
tempo**: com cortes por ano, cada ano teria sempre um quarto das UFs em
cada classe e 2010 sairia igual a 2050. Com cortes fixos, 2000 é inteiro na
classe 1 e 2070 inteiro na classe 4. O custo: dentro de um ano só, o mapa
separa pouco — em 2025, 22 das 27 UFs estão na classe 2. A tabela ao lado
dá o valor exato de cada UF, e é ela que separa o que o mapa junta.

Os cortes **não mudam com o recorte**: a cor segue o estado, não a posição
dele entre os selecionados (`test_cortes_nao_mudam_com_o_filtro`). As
alternativas medidas estão em
[Documentação dos Gráficos](DOCUMENTACAO_GRAFICOS.md#01--onde-estão-os-60).

Os estados pequenos demais para o cursor (o DF, no enquadramento do país)
são redesenhados ampliados, com contorno branco — a mesma convenção de um
encarte em mapa impresso. A área deles no mapa é falsa de propósito; o
valor não.

## 5. A pirâmide etária

Faixas de 5 anos, de "0-4" a "85-89", e a última **"90+"**. A base do IBGE
termina em 90 e essa idade é um balde aberto — "90 anos ou mais" —, então
a última faixa da pirâmide tem que ser aberta também. Se fosse desenhada
até 100+, todo o balde cairia em "90-94" e as faixas acima sairiam vazias.
`IDADE_TOPO` em `src/charts.py` prende a coincidência.

Homens à esquerda (valores negativos), mulheres à direita. A soma das
faixas é a população do recorte, sem perda (`test_faixas_somam_a_populacao`).

## 6. Homens e mulheres

Soma da população por sexo no recorte e no ano. O toggle "Apenas ≥ 60 anos"
restringe à idade ≥ 60 antes de somar. O sexo é o da planilha do IBGE
(Homens/Mulheres), sem outra categoria.

## 7. Evolução populacional

Soma da população total do recorte, ano a ano, 2000 a 2070. Linha sólida
até 2022 (estimativa), tracejada de 2023 em diante (projeção), com a
fronteira marcada e o **pico** anotado — o ano em que a população do
recorte para de crescer.

Para o Brasil, o pico é **2041, com 220,4 milhões**; em 2070 são 199,2
milhões, menos que hoje. Cada UF vira num ano: AL e RS em 2026, RJ em 2027,
SP em 2036 — e MT ainda cresce em 2070.

**O eixo vertical não começa em zero**, de propósito: começando em zero, a
subida e a queda viram uma ondulação de 10% numa linha quase reta, e o
pico — que é a informação — some.

## 8. Os recortes

| Recorte | O que soma |
|---|---|
| Todos os estados | as 27 UFs |
| Norte | AC, AM, AP, PA, RO, RR, TO |
| Nordeste | AL, BA, CE, MA, PB, PE, PI, RN, SE |
| Centro-Oeste | DF, GO, MS, MT |
| Sudeste | ES, MG, RJ, SP |
| Sul | PR, RS, SC |
| Escolher estados… | os marcados; nenhum marcado mostra todos |
| Estado em foco (clique no mapa) | só ele, dentro do recorte acima |

Regiões são as Grandes Regiões do IBGE. Todo número do painel — KPIs,
gráficos, e60 — é recalculado sobre o recorte; o mapa e a tabela mostram o
recorte inteiro mesmo com um estado em foco, para que dê para clicar em
outro.

## 9. O que os números não dizem

- **Projeção é hipótese, não previsão.** De 2023 em diante os números
  dependem das hipóteses do IBGE sobre fecundidade, mortalidade e migração.
  A revisão seguinte vai mudá-los.
- **As UFs convergem, por hipótese.** A dispersão do `e0` entre estados cai
  de 5,3 anos (2025) para 1,2 (2070). Isso é a hipótese de convergência do
  IBGE, não um fato observado — o achatamento das diferenças no futuro não
  deve ser lido como dado.
- **Sem município.** Nenhuma leitura abaixo da UF é possível com esta base.
- **Sem cor, raça, renda ou escolaridade.** A projeção é só por idade e
  sexo.
- **O "vs ano anterior" compara projeção com projeção** a partir de 2024.
  Uma variação de 3% entre 2025 e 2026 é a taxa que o modelo assume, não
  uma medição.

## 10. Como conferir

Os totais por UF e por idade batem com a tab1 do IBGE por construção — o
parquet é a planilha. As conferências feitas:

| Quando | Contra o quê | Resultado |
|---|---|---|
| 04/set/2026 | Estimativas 2025 (DOU) e tab1, sobre a base municipal antiga | 27 UFs exatas; 60+ com 4 pessoas de diferença |
| 15/set/2026 | base antiga × tab1, 2010-2025, célula a célula | 8 de 69.984 células divergem, no máximo 66 pessoas |
| 15/set/2026 | `e60` ponderado × `e60` oficial do Brasil | ≤ 0,02 ano em 2010, 2025, 2050 e 2070 |

Para refazer: `python scripts/preparar_projecao.py <pasta das planilhas>` e
`pytest tests/test_numeros.py`. Os valores de referência (população total
2010/2025/2070, 60+ em 2010/2025, pico em 2041, e60 do Brasil) estão no
próprio teste. Detalhes em [Conferência dos dados](historico/conferencia-dados.md) e
[Levantamento das projeções](historico/levantamento-projecoes.md).
