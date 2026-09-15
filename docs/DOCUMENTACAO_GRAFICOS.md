# Documentação dos Gráficos — Envelhecimento Populacional

Por que cada gráfico existe, como é calculado e onde está o código.

## 01 · Onde estão os 60+

**Por quê:** primeira leitura visual do envelhecimento populacional — onde a proporção de idosos é mais alta no Brasil.

**Como é calculado:** `src/charts.py::processar_dados()` agrega a população por UF em dois totais: `total` (todas as idades) e `idosos` (idade ≥ 60), então calcula `pct_idosos = idosos / total * 100`. O mapa é um `GeoJsonLayer` do deck.gl, via pydeck, com a cor de cada UF interpolada em Python na rampa `#084c96 → #2B7BB9 → #63b3ed` e casada à malha pela sigla.

**Código:** `src/mapa.py::deck()`, com a legenda em `src/mapa.py::legenda()`

**Escala em quartis, com cortes fixos.** O mapa tem quatro classes, e os
cortes (11,4 / 19,7 / 29,9%) são calculados **uma vez sobre todos os anos
(2000-2070) e todas as UFs** — não por ano e não sobre o filtro.

Por ano não serviria: quartil é medida relativa e sempre põe um quarto das
UFs em cada classe. O mapa de 2010 e o de 2050 sairiam iguais e o
envelhecimento do país ficaria invisível. Com corte fixo o mapa escurece
década a década — é o que ele existe para mostrar.

**Os cortes foram redefinidos em 15/set/2026**, quando a base passou de
2010-2025 para 2000-2070. A proporção de 60+ vai de 4% a 40% no período, e
quatro cortes que cubram tudo isso separam pouco dentro de um ano. As três
alternativas, medidas (UFs por classe, da mais clara à mais escura):

| Cortes | 2010 | 2025 | 2040 | 2050 | 2070 |
|---|---|---|---|---|---|
| fixos em 2010-2025 (antigos) | 13/11/3/0 | 2/3/4/18 | 0/0/0/27 | 0/0/0/27 | 0/0/0/27 |
| **fixos em 2000-2070 (atuais)** | 23/4/0/0 | 4/22/1/0 | 0/6/21/0 | 0/0/17/10 | 0/0/0/27 |
| por ano | 7/7/7/6 sempre | | | | |

Os antigos pintavam 2040 em diante inteiro na classe mais escura: três décadas
de mapa igual. Os atuais perdem contraste em 2025 (22 UFs numa classe) em
troca de o mapa continuar mudando até 2070. A tabela 02, ao lado, dá o valor
exato de cada UF no ano — é ela que separa o que o mapa junta.

Sobre o filtro, muito menos: recalcular sobre os estados selecionados faria
os sobreviventes mudarem de cor a cada filtro, e a cor passaria a descrever a
posição do estado no recorte em vez da proporção dele. Preso em
`test_cortes_nao_mudam_com_o_filtro`.

O custo assumido é o da tabela acima: contraste dentro de um ano trocado
por comparabilidade entre anos.

**Clicar num estado põe o painel nos dados dele.** KPIs, sexo, pirâmide e
evolução passam a ser só daquele estado; o hero diz "PE em foco". Clicar de
novo (ou no ✕ que o Streamlit põe sobre o mapa) solta. O recorte do seletor
continua valendo como **contexto**: o mapa e a tabela seguem mostrando o
recorte inteiro — o estado em foco opaco e com contorno grosso, os outros
esmaecidos (`ALFA_FORA_DE_FOCO`) — porque é no mapa que se escolhe o
próximo. Se o mapa passasse a mostrar só o estado clicado, não haveria onde
clicar para trocar.

Três decisões de implementação que valem saber:

- **Sem `st.rerun()`.** O clique chega por `on_select="rerun"` e é lido de
  `st.session_state[chave_mapa]` **antes** de o mapa ser desenhado — o
  Streamlit expõe o estado da interação anterior desde o início do run. É o
  que permite os KPIs, que ficam acima do mapa, já saírem filtrados.
- **A chave do widget muda com o recorte.** A seleção do widget sobrevive à
  troca de recorte: com MG em foco, ir para "Sul" soltava o foco e voltar
  para "Todos" trazia MG de volta sozinho. Chave nova a cada recorte é
  widget novo, sem memória. O foco sobrevive à troca de **ano**, de
  propósito — comparar 2026 e 2050 do mesmo estado é uma leitura que vale.
- **A página não pula para o topo.** O script do botão de tema rolava a
  página ao topo a cada rerun, e o mapa fica no meio da página: o leitor
  clicava e era jogado para longe do que tinha clicado. Agora rola só no
  primeiro carregamento.

**A roda do mouse não dá zoom.** Rolar a página com o cursor sobre o mapa
aplicava zoom e desenquadrava — e o mapa ocupa meia tela, então acontecia o
tempo todo. O caminho declarativo não existe: o Streamlit passa
`controller={true}` fixo ao `<DeckGL>` e descarta o que vier no JSON. A trava
é no DOM, interceptando `wheel` na captura **sem** `preventDefault`, para a
página seguir rolando. Os botões de zoom foram escondidos junto: sem a roda
eles seriam o único jeito de desenquadrar, e zoom num coroplético de recorte
fixo não acrescenta leitura.

**O Distrito Federal ganha um disco.** No enquadramento do país ele mede uns
9x5 px, e acertá-lo com o ponteiro era pontaria. `pickingRadius` não resolve
— o deck só procura no raio quando não há nada sob o cursor, e o DF é cercado
por Goiás; medido, a 6 px do DF o tooltip mostrava GO. A solução é redesenhá-lo
**ampliado em torno do próprio centro, mantendo a forma** — mesma cor da
classe, para não inventar informação, e contorno branco sinalizando que
aquele polígono está fora de escala, como um encarte ampliado em mapa
impresso. Some sozinho quando o recorte aproxima e a UF já está grande.

Uma primeira versão usava um disco. Resolvia a pontaria, mas trocava a forma
reconhecível do DF por um círculo — descaracterizava o mapa sem necessidade.

**Sem basemap.** Era um `choropleth_mapbox` sobre ladrilhos `carto-positron` até a CARTO passar a exigir chave — o painel em produção desenhava "API KEY REQUIRED" repetido sob a malha. Trocar de fornecedor de ladrilho só adiaria o problema: um coroplético por estado não precisa de rua nem de rio embaixo, a informação é a cor da UF. Sem ladrilho não há chave, nem requisição a terceiro, nem fornecedor que possa repetir isto.

**A malha é pré-processada.** `scripts/preparar_geometria.py` roda uma vez e escreve `data/ufs.geojson`: simplificação topológica (85.585 → 4.469 vértices), 5 casas decimais e só a propriedade `sigla`. Só as UFs selecionadas são enviadas, e o spec sai sem indentação. O payload caiu de 1.953 KB para 98 KB no Brasil e 3 KB numa UF — ver [Performance](performance.md).

**O enquadramento acompanha o filtro**, em vez do `zoom=3.2` fixo de antes. Ao calcular os limites, ilhas oceânicas afastadas são descartadas: **Fernando de Noronha é de Pernambuco** e, sem esse cuidado, selecionar PE desenharia um mapa de oceano.

**Sem fallback.** O anterior existia porque o Mapbox podia falhar — dependia de um terceiro pela rede. Sem ladrilho não há essa falha, e manter uma segunda rota de mapa em Plotly significaria manter código morto que ninguém exercita.

## 02 · Estados mais envelhecidos

**Por quê:** o mapa mostra o padrão geográfico, mas não é fácil ler os valores exatos — essa tabela complementa com o ranking preciso.

**Como é calculado:** ordena `df_idosos` por `pct_idosos` descendente e pega os 15 primeiros (ou menos, se houver menos estados filtrados).

**Código:** `src/utils.py::html_top5()` monta o HTML da tabela; a ordenação acontece em `app.py`.

## 03 · Homens e mulheres

**Por quê:** proporção de homens e mulheres na população total (ou só entre os idosos, via toggle).

**Como é calculado:** `src/charts.py::fig_pizza()` agrupa por `sexo` e soma `populacao`. O toggle "Apenas ≥ 60 anos" filtra a base por idade antes de agregar.

**Código:** `src/charts.py::fig_pizza()`

## 04 · Pirâmide etária

**A última faixa é "90+", porque a base termina num balde aberto aos 90.** A
faixa final tem que coincidir com o balde da base, e `IDADE_TOPO` em
`src/charts.py` prende isso. A lição veio da base anterior, que parava em 80:
enquanto a pirâmide desenhava faixas até 100+, os 4,96 milhões de 80+ caíam
inteiros em "80-84" — 1,8x o valor real — e as faixas acima ficavam zeradas,
sugerindo que ninguém passa dos 85. Ver
[Conferência dos dados](historico/conferencia-dados.md).

**Por quê:** visão clássica de demografia — a forma da pirâmide (base larga vs. topo largo) indica se a população está envelhecendo ou é predominantemente jovem.

**Como é calculado:** `processar_dados()` cria faixas etárias de 5 em 5 anos (`0-4`, `5-9`, ..., `85-89`, `90+`). O gráfico plota homens como valores negativos e mulheres como positivos, convenção padrão de pirâmide etária, pra ficarem em lados opostos do eixo zero.

**Código:** `src/charts.py::fig_piramide()`

## 05 · Evolução populacional (2000–2070)

**Por quê:** é o único gráfico do painel que mostra **para onde** a população
vai, e a projeção do IBGE conta uma história que nenhum retrato de um ano
conta: o Brasil cresce até **2041** (220,4 milhões) e chega a 2070 com menos
gente do que tem hoje (199,2 milhões). Cada UF vira num ano: RS e AL em
2026, RJ em 2027, SP em 2036 — e MT ainda cresce em 2070.

**Como é calculado:** `src/data.py::carregar_evolucao()` agrega população total por UF e ano (cacheado como recurso, independente do filtro de ano ativo). `fig_evolucao()` soma só as UFs selecionadas e converte para milhões de habitantes.

**Duas linhas, uma fronteira.** Sólida até 2022, que é o último ano que o
IBGE classifica como estimativa; tracejada de 2023 em diante, que é
projeção. A fronteira aparece como linha vertical rotulada — tracejado sem
legenda lê como estilo, não como significado. O ponto de 2022 entra nas duas
séries para a linha não ter buraco. Antes da troca de base o gráfico ia até
2025 em linha sólida, apresentando três anos de projeção como se fossem
contagem.

**O eixo y não começa em zero, de propósito.** Somando o país a série vai de
174 M a 220 M e volta a 199 M. Num eixo desde o zero isso é uma ondulação de
10% numa linha quase reta, e o pico — que é a história — some. O pico vem
anotado com ano e valor, para o leitor não ter que procurá-lo.

**Código:** `src/charts.py::fig_evolucao()`

## KPIs do topo

Os quatro cards são calculados em `app.py::_indicadores()` sobre as UFs
selecionadas, com comparação automática ao ano anterior via
`src/utils.py::_delta_html()`. Sem ano anterior na base, a variação não
aparece.

| Card | O que é |
|---|---|
| **Pessoas com 60+** | Contagem absoluta; o total do país vai no subtítulo, como denominador |
| **Proporção de 60+** | A mesma contagem sobre a população total |
| **Índice de envelhecimento** | Pessoas de 60+ para cada 100 crianças de 0 a 14 anos |
| **Esperança de vida aos 60** | Anos que, em média, ainda vive quem chegou aos 60. Valor oficial do IBGE (`e60`, tab4), não uma conta nossa; para um recorte de UFs, média ponderada pela população de 60+ de cada uma — reproduz o valor oficial do Brasil a 0,02 ano |

### Três cards que saíram, e por quê

**"Idade média"** saiu em 15/set/2026 pela esperança de vida aos 60. Não
estava errada — com a base até 90+ ela até passou a bater com o IBGE no
centésimo. Mas fala da população inteira; um painel sobre 60+ precisa do
número que fala do seu público. O `e60` vai de 21,6 (AL) a 24,5 anos (DF) em
2025, e é a única medida de *longevidade* propriamente dita no painel.

**"Proporção feminina"** mostrava 51,2% de mulheres na população total. Dois
problemas: não fala de envelhecimento — é fato demográfico geral — e é
estruturalmente imóvel. Medido: 51,09% em 2010 contra 51,25% em 2025, 0,16
ponto em quinze anos. O "▲ 0,0% vs ano anterior" que aparecia não era do ano,
era do indicador. Um card que nunca se move ocupa um quarto da faixa mais
visível do painel para não informar nada.

Entrou no lugar o índice de envelhecimento, que foi de 43 para 85 no mesmo
período — dobrou.

**"População total"** virou subtítulo do primeiro card. O painel é sobre a
população de 60+; ela merece a primeira posição, e o total do país serve
melhor como denominador do que como indicador próprio.

### Uma cor só

Os quatro cards usam o roxo da marca. Antes cada um tinha um matiz distinto
(azul, laranja, roxo, verde) que não codificava nada — cor decorativa, que o
olho tenta interpretar sem encontrar significado. E depois da troca de marca a
classe chamada `.blue` ainda pintava de roxo.

## Por que não há um ranking de estados

Havia, na seção 06: um gráfico de barras com a proporção de 60+ por UF,
ordenado. Saiu porque mostrava **o mesmo número** do mapa (01) e da tabela
(02) — a mesma métrica em três formas, na mesma página.

A tabela ficou porque é a que complementa o mapa: o mapa dá o padrão
geográfico e não dá valor exato; a tabela dá o valor exato e não dá o padrão.
O ranking em barras não acrescentava um terceiro ângulo, só repetia o
segundo.

O sintoma era a redação: os três títulos precisavam dizer "proporção de
idosos por estado" de jeitos ligeiramente diferentes para não parecerem
duplicados. Quando o texto se contorce assim, em geral o problema é o
conteúdo, não a palavra.

## Vocabulário

O painel diz **"60+"** e **"pessoas com 60 anos ou mais"**, não "idosos", em
tudo que o leitor vê: títulos, cards, legenda do mapa, cabeçalho da tabela e
tooltips.

Não é preciosismo — é consistência. Durante um tempo o painel usou os dois:
os títulos falavam em "60+" e a legenda do mapa em "% Idosos". Vocabulário
misturado faz o leitor parar para conferir se são a mesma métrica, e isso
custa mais atenção do que a palavra economiza.

Nos nomes internos (colunas `pct_idosos`, `df_idosos`) o termo permanece —
ali ele não é lido por ninguém de fora e trocá-lo mexeria em toda a camada de
dados sem ganho.
