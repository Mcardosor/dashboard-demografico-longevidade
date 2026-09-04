#!/bin/bash
set -e

echo "==> Atualizando repositório..."
git pull origin main

# `up -d --build` no lugar de `down` + `build --no-cache` + `up`.
#
# O `down` derrubava o painel ANTES de construir, então uma falha de build
# deixava o site fora do ar. Assim o container antigo continua servindo e só é
# trocado depois que a imagem nova fica pronta.
#
# O `--no-cache` reconstruía tudo, inclusive o `pip install`, a cada deploy —
# minutos gastos para reinstalar dependências que não mudaram. O cache do
# Docker já se invalida sozinho quando o `requirements.txt` muda.
echo "==> Construindo a imagem e trocando o container..."
docker compose up -d --build

echo "==> Status:"
docker compose ps

echo ""
echo "Painel em: https://painel.cenarios.unb.br/cenarios/demografico-longevidade/"
