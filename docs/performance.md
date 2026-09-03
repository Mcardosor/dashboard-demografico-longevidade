# Performance — linha de base

Medido em 02/set/2026, antes de qualquer otimização. Reproduzir com:

```bash
docker run --rm -v "$PWD:/app" -w /app demografico:base python -m scripts.medir_performance
```

Mediana de 5 execuções, em milissegundos, **sem** o cache do Streamlit.
Ano de referência 2025.

## Camada de dados

| Operação | Mediana | Pior |
|---|---:|---:|
| `carregar_geojson` | 81,8 | 113,1 |
| `_carregar_base` | 5.770,4 | 6.246,0 |
| `carregar_dados(ano)` | 819,6 | 887,4 |
| `carregar_evolucao` | 1.637,6 | 1.740,1 |
| `processar_dados` | 2,2 | 3,0 |

Estes são custos **de partida**, não por interação: as quatro primeiras são
cacheadas por `@st.cache_data`/`@st.cache_resource` e rodam uma vez por
processo. O que o usuário paga a cada clique é `processar_dados` — 2,2 ms,
duas vezes (ano atual e anterior) — mais a montagem das figuras.

## Figuras — tempo de montagem e payload

| Figura | BR (27 UFs) | Sudeste (4) | PE (1) |
|---|---:|---:|---:|
| **`fig_mapa`** | **194,1 ms · 1.953 KB** | **195,5 ms · 1.953 KB** | **172,6 ms · 1.953 KB** |
| `fig_pizza` | 26,3 ms · 5 KB | 26,2 ms · 5 KB | 26,5 ms · 5 KB |
| `fig_piramide` | 18,9 ms · 6 KB | 18,9 ms · 6 KB | 18,5 ms · 5 KB |
| `fig_ranking` | 28,2 ms · 5 KB | 28,3 ms · 4 KB | 28,2 ms · 4 KB |
| `fig_evolucao` | 28,4 ms · 5 KB | 27,9 ms · 5 KB | 27,9 ms · 5 KB |

## Leitura

**O mapa é o painel inteiro, em custo.** Custa 194 ms contra 19–28 ms do
próximo gráfico, e despacha 1.953 KB contra 4–6 KB. São 350× mais bytes que
qualquer outra figura, e a soma de tudo que não é mapa dá 20 KB.

**O payload não responde ao filtro.** 1.953 KB com as 27 UFs, 1.953 KB com o
Sudeste, 1.953 KB com Pernambuco sozinho. O `choropleth_mapbox` recebe o
GeoJSON inteiro por parâmetro e o embute no JSON da figura; o filtro de
estados muda só quais delas ganham cor. Quem olha um estado paga pela malha
do país.

E não é custo de primeira carga: o JSON da figura muda a cada troca de ano,
de estado ou de tema — as cores fazem parte dele —, então os 1,9 MB voltam
pela rede a cada clique. Num enlace de 10 Mbit/s são cerca de 1,6 s por
interação, invisíveis em `localhost`. É a mesma armadilha registrada em
`paineis/sinan/docs/performance.md`: medir localmente esconde o custo de rede.

## De onde vêm os 1,9 MB

O `data/brazil-states.geojson` tem 3,4 MB em disco e 2,1 MB serializado sem
indentação — **um terço do arquivo é recuo**. Dentro dele:

| | |
|---|---:|
| Feições | 27 |
| Vértices | 85.585 |
| Vértices por UF | ~3.170 |
| Casas decimais | 6 (~10 cm) |

Num mapa do Brasil de ~600 px de largura, 85 mil vértices são muito mais
detalhe do que existe pixel. Cada feição ainda carrega `cartodb_id`,
`created_at`, `updated_at`, `name`, `regiao_id` e `codigo_ibg` — o mapa usa
`sigla`, e só.

## O basemap, que além de tudo quebrou

O `mapbox_style="carto-positron"` puxa ladrilhos da CARTO, que passou a
exigir chave: o painel em produção desenha hoje o carimbo **"API KEY
REQUIRED — docs.carto.com/basemaps"** repetido sob a malha. Some do custo
medido acima porque é requisição do navegador, não payload do Streamlit, mas
é o motivo de o mapa estar sendo refeito.

---

# O que foi feito — 02/set/2026

O mapa saiu do Plotly/CARTO e foi para **pydeck, sem basemap**
(`map_provider=None`). Três mudanças independentes, medidas separadamente.

## 1. A malha, pré-processada em disco

`scripts/preparar_geometria.py` roda uma vez e escreve `data/ufs.geojson`.
O `brazil-states.geojson` cru continua versionado como entrada, mas não é mais
lido em execução.

| | Antes | Depois | |
|---|---:|---:|---:|
| Arquivo | 3,38 MB | 0,10 MB | −97% |
| Vértices | 85.585 | 4.469 | −95% |
| Casas decimais | 6 | 5 | |
| Propriedades por feição | 6 | 1 | |
| `carregar_geojson` | 81,8 ms | 4,5 ms | −94% |

Erro de área: **0,006%**. Pior sobreposição entre estados: **0,00 km²**.

### Por que topológica, e por que `shared_coords=True`

O `simplify` do shapely trata cada polígono isoladamente, então vizinhos
simplificam a divisa comum de formas diferentes e o mosaico se rompe. Com
simplificação topológica as arestas compartilhadas viram arcos e são
simplificadas uma vez só.

O sinan usa `shared_coords=False`. **Aqui isso estaria errado**, e a medição
mostrou: sobre esta malha, `False` *introduz* 99,74 km² de sobreposição numa
malha que vinha com zero — pelo mesmo número de vértices (4.455 contra 4.469)
e o mesmo erro de área. Com `True`, zero. As duas foram medidas antes de
escolher.

### O que a simplificação custa

A tolerância é relativa ao bbox do **Brasil**, então é meio pixel na vista do
país e cerca de 3 px quando se seleciona uma UF sozinha — aí o contorno fica
visivelmente facetado. É perda consciente: a vista de uma UF é um polígono de
cor única, onde a forma não carrega informação, e a vista do país, que é a
informativa, não mostra o defeito.

**Medido e não aplicado:** dobrar a resolução (`DIVISOR = 2400`) leva a 8.643
vértices e ~190 KB de payload no Brasil. Cobra o dobro justamente na vista
onde o ganho não aparece. Fica registrado como a alavanca, se alguém quiser.

## 2. Só as UFs visíveis, e o spec sem indentação

O `choropleth_mapbox` recebia o GeoJSON inteiro por parâmetro. O
`GeoJsonLayer` recebe só as feições do recorte, e `mapa._compactar` faz o
pydeck serializar sem `indent=2`.

| Payload do mapa | Antes | Depois | |
|---|---:|---:|---:|
| BR (27 UFs) | 1.953 KB | **98 KB** | −95% |
| Sudeste (4) | 1.953 KB | **19 KB** | −99% |
| PE (1) | 1.953 KB | **3 KB** | −99,8% |

O payload passou a **responder ao filtro**, que era o defeito central: quem
olhava um estado pagava pela malha do país. Num enlace de 10 Mbit/s, a
interação típica sobre o Brasil cai de ~1,6 s de transferência para ~0,08 s.

## 3. A inversão de custo

| Figura (BR) | Antes | Depois |
|---|---:|---:|
| **mapa** | **194,1 ms** | **13,5 ms** |
| `fig_pizza` | 26,3 ms | 32,0 ms |
| `fig_piramide` | 18,9 ms | 25,4 ms |
| `fig_ranking` | 28,2 ms | 32,1 ms |
| `fig_evolucao` | 28,4 ms | 34,0 ms |

O mapa era a figura mais cara do painel por 7×; passou a ser **a mais
barata**. `test_mapa_deixou_de_ser_a_figura_mais_cara` prende a inversão.

Os quatro gráficos do Plotly subiram de 5 a 6 ms cada. É a passagem de
**plotly 5.24.1 para 6.3.1**, feita na mesma leva porque a linha `mapbox` foi
removida na 6. Não compensava investigar: os cinco somados custam menos do
que o mapa sozinho custava.

## 4. Dois defeitos achados durante a troca

**Fernando de Noronha é de Pernambuco.** O bbox cru de PE tem 9,0° de largura
contra 6,5° do estado continental — selecionar PE desenharia quase só oceano.
`mapa._limites` descarta partes de terra afastadas mais de 1° do corpo, como
o `limites_uteis` do sinan, mas em Python puro (geopandas é dependência de
build, não de runtime). Apareceu como falha de um teste de bounding box.

**`__MAP_STYLE__`.** Com `map_provider=None` mas sem `map_style=None`, o
pydeck deixa esse sentinela no spec. O deck.gl lê a string como URL relativa
e busca `/cenarios/demografico/__MAP_STYLE__` a cada render; o Streamlit
responde 200 com o `index.html` e o console enche de "Unexpected token '<'".
Uma requisição inútil por render — invisível nos testes que eu tinha, achada
no painel de rede do navegador. `test_nao_emite_o_sentinela_de_estilo`
existe para a próxima não passar batido.

## 5. O basemap voltou sem ninguém notar — e como foi pego

Registrado em 03/set/2026, depois do painel Longevidade ir ao ar com o defeito.

O commit que tirou o sentinela `__MAP_STYLE__` do spec (item 4 acima) passou
`map_style=None`. **No pydeck, `None` não significa "sem mapa":** significa
"deixe o Streamlit escolher o estilo pelo tema". Sem estilo no spec, o
frontend aplicou o padrão dele — `mapbox://styles/mapbox/light-v8` — e o
painel voltou a puxar ladrilhos, sprites, fontes e **telemetria**
(`events.mapbox.com`), com um token de demonstração embutido na versão de
`react-map-gl` que o Streamlit empacota.

Trocamos a CARTO por outro fornecedor de ladrilho sem perceber. O item 4
tinha resolvido uma requisição inútil por render e criado nove.

**Por que os testes não pegaram.** Eles liam o spec, e o basemap era
acrescentado pelo frontend, fora do spec. Nenhum teste unitário sobre o JSON
podia ver isso. `test_estilo_vazio_e_explicito` passa a exigir um estilo
vazio em vez da *ausência* de estilo — ausência é convite ao padrão alheio —,
mas o flanco real só se vê no painel de rede do navegador, e isso está
anotado dentro do próprio teste.

**Por que a verificação local não pegou.** Verifiquei em `localhost`, numa
rede que bloqueia `api.mapbox.com` — a mesma que bloqueia `github.com` e que
obrigou a subir o primeiro commit pela API. Os ladrilhos falhavam em silêncio
e o mapa aparecia limpo. **Falso negativo por rede quebrada**: o ambiente de
teste era mais restritivo que o de produção, então escondeu o defeito em vez
de revelá-lo.

**A correção, em duas tentativas.** Primeiro um objeto
`{"version": 8, "sources": {}, "layers": []}` no `mapStyle`. Não bastou: o
servidor mandava o objeto certo — conferido dentro do container —, mas o
frontend descarta objeto e cai no padrão. O que funciona é o mesmo estilo
como **`data:` URI**: string, então sobrevive até o componente, e com o
conteúdo embutido, então nem para buscar o estilo sai requisição.

| Hosts externos por carga | Antes | Depois |
|---|---:|---:|
| `api.mapbox.com` | 8 requisições | **0** |
| `events.mapbox.com` | 1 (telemetria) | **0** |

Medido na URL pública, não em `localhost`.

**A lição que fica.** "Não pede ladrilho a ninguém" é afirmação sobre o
*navegador*, e só o navegador pode confirmá-la. Teste de spec verifica o que
mandamos; o painel de rede verifica o que acontece. Para esta propriedade,
apenas o segundo vale — e ele precisa rodar contra produção, ou contra uma
rede que não minta por omissão.

---

# Alvos presos em teste

| Orçamento | Alvo | Medido | Onde é preso |
|---|---:|---:|---|
| **Payload do mapa**, Brasil | ≤ 200 KB | **98 KB** | `tests/test_mapa.py` |
| **Payload do mapa**, uma UF | ≤ 20 KB | **3 KB** | `tests/test_mapa.py` |
| **Servidor**, por interação | ≤ 400 ms | **~137 ms** | `tests/test_performance.py` |
| **Malha**, vértices | ≤ 6.000 | **4.469** | `tests/test_geo.py` |
| **Malha**, arquivo | ≤ 200 KB | **105 KB** | `tests/test_geo.py` |

"Interação" é o trabalho completo de trocar o ano ou a seleção: processar a
base do ano atual e do anterior, montar o mapa e os quatro gráficos.

Os tetos têm folga de propósito. Prender o número medido faria o teste falhar
por ruído de máquina; o que eles pegam é regressão de ordem de grandeza.

## O que ainda não foi medido

- Tempo percebido ponta a ponta, no navegador
- Comportamento com vários usuários simultâneos
- `_carregar_base` leva 6–8 s no primeiro acesso do processo. É pago uma vez,
  e a thread de warmup em `app.py` o antecipa, mas nunca foi medido do ponto
  de vista de quem abre o painel primeiro.
