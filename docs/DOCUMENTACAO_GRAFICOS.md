# Documentação dos Gráficos — Envelhecimento Populacional

Por que cada gráfico existe, como é calculado e onde está o código.

## 01 · Onde estão os 60+

**Por quê:** primeira leitura visual do envelhecimento populacional — onde a proporção de idosos é mais alta no Brasil.

**Como é calculado:** `src/charts.py::processar_dados()` agrega a população por UF em dois totais: `total` (todas as idades) e `idosos` (idade ≥ 60), então calcula `pct_idosos = idosos / total * 100`. O mapa é um `GeoJsonLayer` do deck.gl, via pydeck, com a cor de cada UF interpolada em Python na rampa `#084c96 → #2B7BB9 → #63b3ed` e casada à malha pela sigla.

**Código:** `src/mapa.py::deck()`, com a legenda em `src/mapa.py::legenda()`

**Escala em quartis, com cortes fixos.** O mapa tem quatro classes, e os
cortes (9,5 / 11,8 / 13,8%) são calculados **uma vez sobre todos os anos e
todas as UFs** — não por ano e não sobre o filtro.

Por ano não serviria: quartil é medida relativa e sempre põe um quarto das
UFs em cada classe. Medido, dá 7/6/7/7 em 2010 e 7/6/7/7 em 2025 — os dois
mapas sairiam iguais e o envelhecimento do país ficaria invisível. Com corte
fixo, 2010 não tem nenhuma UF na classe mais alta e 2025 tem dezoito.

Sobre o filtro, muito menos: recalcular sobre os estados selecionados faria
os sobreviventes mudarem de cor a cada filtro, e a cor passaria a descrever a
posição do estado no recorte em vez da proporção dele. Preso em
`test_cortes_nao_mudam_com_o_filtro`.

O custo assumido é que em 2025 dois terços das UFs caem na classe mais alta —
o mapa perde distinção dentro do ano atual em troca de ser comparável entre
anos.

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

**Por quê:** visão clássica de demografia — a forma da pirâmide (base larga vs. topo largo) indica se a população está envelhecendo ou é predominantemente jovem.

**Como é calculado:** `processar_dados()` cria faixas etárias de 5 em 5 anos (`0-4`, `5-9`, ..., `100+`). O gráfico plota homens como valores negativos e mulheres como positivos, convenção padrão de pirâmide etária, pra ficarem em lados opostos do eixo zero.

**Código:** `src/charts.py::fig_piramide()`

## 05 · Evolução populacional (2010–2025)

**Por quê:** tendência histórica da população total dos estados selecionados, complementando o retrato de um único ano dado pelos outros gráficos.

**Como é calculado:** `src/data.py::carregar_evolucao()` agrega população total por UF e ano (cacheado como recurso, independente do filtro de ano ativo). `fig_evolucao()` soma só as UFs selecionadas e converte para milhões de habitantes.

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
| **Idade média** | Média ponderada pela população de cada idade |

### Dois cards que saíram, e por quê

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
