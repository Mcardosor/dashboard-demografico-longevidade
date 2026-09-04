# Deploy na VM

A VM é a `cenarios-vm` (10.20.10.64, hostname `wrdocker2`), **acessível só pela
VPN**. Ela hospeda todos os painéis do Cenários em containers, com um nginx
local fazendo o roteamento por caminho.

| Painel | Porta no host | Rota |
|---|---:|---|
| demografico | 8501 | `/cenarios/demografico` |
| tb | 8502 | `/cenarios/tb` |
| tbrecife | 8503 | `/cenarios/tbrecife` |
| tbpe | 8504 | `/cenarios/tbpe` |
| Leprosy | 8505 | `/cenarios/Leprosy/` |
| superset | 8506 | `/cenarios/superset/` |
| sinan | 8507 | `/cenarios/sinan` |
| **demografico-longevidade** | **8508** | `/cenarios/demografico-longevidade` |

O `deploy.sh` na raiz cobre as atualizações do dia a dia (`git pull`, rebuild,
sobe). O que está abaixo é o **bootstrap**, que roda uma vez.

## 1. O código na VM

O repositório é privado, então `git clone` por HTTPS pede credencial. Confira
o que a VM já tem antes de escolher:

```bash
ssh cenarios-vm 'git config --global credential.helper; ls ~/.ssh/*.pub'
```

Três caminhos, do mais simples ao mais controlado:

- **Deploy key** — gerar um par na VM e cadastrar a pública em
  Settings → Deploy keys do repositório, só leitura. É o mais adequado: a
  chave serve a um repositório e nada mais.
- **`rsync` da máquina de trabalho** — dispensa credencial na VM, mas o
  diretório lá deixa de ter `git` e o `deploy.sh` para de funcionar; cada
  atualização vira um novo `rsync`.
- **Tornar o repositório público** — resolve na hora e é o que os outros
  painéis fazem, mas é decisão de exposição, não de conveniência.

Com a credencial resolvida:

```bash
ssh cenarios-vm
git clone https://github.com/Mcardosor/dashboard-demografico-longevidade.git
cd dashboard-demografico-longevidade
docker compose up -d --build
docker compose ps        # espera-se "healthy" após ~40 s
curl -f http://localhost:8508/cenarios/demografico-longevidade/_stcore/health
```

O `start_period` do healthcheck é de 40 s porque `_carregar_base` lê 23 MB de
parquet no primeiro acesso do processo. Antes disso o container aparece como
`starting`, não como quebrado.

## 1.5. O cartão na página inicial

A rota do nginx torna o painel **alcançável**; ela não o torna
**encontrável**. Quem chega em `https://painel.cenarios.unb.br/` vê uma grade
de cartões, e um painel sem cartão ali só existe para quem já sabe a URL.

A página não está em repositório nenhum: é um HTML solto em
`/var/www/frontpage/index.html`, versionado por cópias `.bak-<data>` ao lado.
Editar publica na hora — não precisa recarregar o nginx.

```bash
ssh cenarios-vm 'cp /var/www/frontpage/index.html /var/www/frontpage/index.html.bak-$(date +%Y%m%d-%H%M%S)'
```

O cartão segue o formato dos vizinhos:

```html
    <a class="card" href="/cenarios/demografico-longevidade">
      <div class="icon">🧓</div>
      <h2>Envelhecimento Populacional</h2>
      <p>Pessoas com 60 anos ou mais no Brasil — proporção por estado em quartis, índice de envelhecimento e pirâmide etária. Plataforma da Longevidade / UnB</p>
      <span class="tag new">Novo</span>
    </a>
```

Ele fica **logo depois do `Dashboard Demográfico`**: os dois compartilham a
base e a diferença é de marca e de recorte, então lado a lado a escolha entre
eles fica óbvia.

**Confira com cache-buster.** `https://painel.cenarios.unb.br/?v=2` — sem
isso o navegador devolve a página antiga e a edição parece ter falhado.

## 2. A rota no nginx

O arquivo é `/etc/nginx/sites-available/telessaude` (com link em
`sites-enabled/`). O bloco novo acompanha o formato dos vizinhos:

```nginx
    location /cenarios/demografico-longevidade {
        proxy_pass         http://localhost:8508;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection $connection_upgrade;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
```

**Faça backup antes de editar** — o diretório já tem vários
`telessaude.bak-*`, sinal de que essa precaução é praxe ali:

```bash
sudo cp /etc/nginx/sites-available/telessaude \
        /etc/nginx/sites-available/telessaude.bak-$(date +%Y%m%d-%H%M%S)
sudo nginx -t            # NUNCA recarregue sem isto passar
sudo systemctl reload nginx
```

`nginx -t` valida a sintaxe antes de aplicar; `reload` não derruba conexões
existentes, ao contrário de `restart`.

### A pegadinha do prefixo

Os `location` daqui são **prefixo sem barra final**, então
`/cenarios/demografico` casa também com `/cenarios/demografico-longevidade`.
Não é conflito: o nginx escolhe o prefixo mais longo, e a rota deste painel
vence. Mas o comportamento é implícito, e quem mexer num dos dois blocos
precisa conferir o outro.

Depois de recarregar, **teste os dois**, não só o novo:

```bash
curl -sI https://painel.cenarios.unb.br/cenarios/demografico-longevidade | head -1
curl -sI https://painel.cenarios.unb.br/cenarios/demografico             | head -1
```

Se o painel antigo passar a devolver a página do novo, é a regra de prefixo
tendo sido resolvida ao contrário do esperado — reverta pelo backup e trate
os dois blocos como `location = ` exato ou com barra final.

## 3. Conferência final

- `https://painel.cenarios.unb.br/cenarios/demografico-longevidade` abre
- o mapa desenha **sem** o carimbo "API KEY REQUIRED" (era o defeito que
  motivou a troca do coroplético — ver [performance](performance.md))
- o painel `demografico` continua no ar, intacto
