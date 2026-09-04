# Identidade visual — Plataforma da Longevidade

Este painel deixou de ser Cenários+ e passou a vestir a marca do **Observatório
da Longevidade / UnB** ([longevidade.unb.br](https://longevidade.unb.br)).

Nada aqui foi escolhido no olho. As cores de marca saíram do CSS do próprio
site; as de gráfico passaram pelo validador do skill `dataviz` — o mesmo
critério do [manual de identidade dos painéis do Cenários][manual].

[manual]: https://claude.ai/code/artifact/32b2dc87-a90e-44c9-8560-5a56312fcb16

## Marca

Lidos das variáveis CSS do site (`--primary` e companhia):

| Papel | Valor | Onde aparece |
|---|---|---|
| Primária | `#6B2F96` | barra, rodapé, `accent` do tema claro |
| Clara | `#8A4BBF` | degrau da rampa |
| Escura | `#4A1F6E` | — |
| Fundo suave | `#F3EDF9` · `#F5F0FA` | hero |
| Borda | `#E4DAF0` | `border_hero` |
| **Acento** | `#AA2DA3` | a flor do logo; `accent2` |

O magenta não veio do CSS: foi **amostrado do JPEG do logo**, onde ocupa 22%
dos pixels da flor.

### Contraste — a troca é ganho, não só estética

| | Branco sobre a cor |
|---|---:|
| `#6B2F96` (Longevidade) | **8,49:1** |
| `#2B7BB9` (Cenários) | 4,53:1 |

O azul do Cenários passava raspando na WCAG AA; o roxo passa com folga, e
também como texto sobre fundo claro (7,98:1).

## O logo

O site serve o logo como **JPEG de fundo branco**, 823×247
(`assets/media9.jpeg`): "Plataforma" em serifada leve, "Longevidade" em bold
pesada, com uma flor de cinco pétalas no lugar do "o".

Aqui ele é **refeito em SVG** (`themes.FLOR_SVG` + `themes.marca_html`), e não
recortado do arquivo. Três motivos: escala sem serrilhar, não carrega uma
caixa branca para dentro do tema escuro, e as pétalas herdam a cor do texto
por `currentColor`.

**A flor muda de cor na barra.** No original ela é magenta sobre branco; na
barra roxa ela é branca com o miolo roxo. `#AA2DA3` sobre `#6B2F96` são dois
roxos vizinhos e empastam — a forma sumiria. O magenta segue sendo o acento
onde há fundo claro.

O tipo do wordmark é fonte de sistema em peso 800, que é o que o próprio site
usa (ele não carrega webfont). **Pendência:** pedir o vetor original ao
Observatório; a reprodução é fiel na forma, não na tipografia exata do JPEG.

## Cores de gráfico

Reproduzir:

```bash
python <skill dataviz>/scripts/validate_palette.py "<hex,hex,...>" \
    --mode light --surface "#f6f8fa"
```

### Rampa sequencial do mapa

| Tema | Degraus |
|---|---|
| Claro | `#BFA1DB #A177C7 #8A4BBF #6B2F96 #552578 #3D1A5C` |
| Escuro | `#E0CDF2 #C6ACE0 #AE8AD2 #9668C4 #7F4DB8 #6B3F9E` |

As duas passam em monotonia de luminosidade, salto mínimo entre degraus, hue
único e contraste da ponta contra a superfície.

**São rampas independentes, não uma o espelho da outra.** A do claro reprova
contra `#0d1117` — a ponta escura fica a 1,35:1 do fundo. Cada tema tem os
seus degraus.

**A primeira tentativa reprovou:** começava em `#D9C7EA`, que dá 1,48:1 contra
`#f6f8fa`, abaixo do piso de 2:1 — o degrau mais claro sumia no fundo.

### De quebra, uma inversão corrigida

O mapa em Plotly ia de `#084c96` (escuro) para `#63b3ed` (claro): **quanto
maior a proporção de idosos, mais clara a UF**. Isso inverte a convenção de
rampa sequencial e faz o olho ler o mapa ao avesso. A nova vai de claro a
escuro, e `test_rampa_vai_de_claro_a_escuro` prende isso nos dois temas.

### Masculino / feminino

| Tema | Masculino | Feminino |
|---|---|---|
| Claro | `#7F4DB8` | `#C0663C` |
| Escuro | `#9E79CC` | `#EA630E` |

**O par óbvio reprova.** Roxo da marca + magenta da flor (`#6B2F96` +
`#AA2DA3`) dá ΔE **5,3** em protanopia e **12,7 mesmo com visão normal de
cor** — abaixo do piso de 15. As duas metades da pirâmide etária ficariam
indistinguíveis para qualquer pessoa, não só para quem tem daltonismo.

Tentei manter as duas séries na família roxa de várias formas. Todas caem: no
tema escuro o roxo claro ainda sai da banda de luminosidade e fica abaixo do
piso de croma, isto é, **lê como cinza**.

O que passa limpo nos dois temas é **roxo + terracota**, com ΔE 23,3 (claro).
E esses terracotas são exatamente os degraus já validados no manual do
Cenários — então há continuidade entre os painéis da casa, não uma cor solta.

### A regra que fica

O roxo é cor de **marca e de magnitude** (barra, rodapé, UI, rampa do mapa).
Não serve como cor de **identidade categórica**, onde o que importa é a
distância entre matizes, não a fidelidade à marca. Confundir as duas coisas é
o que produz um gráfico bonito e ilegível.
