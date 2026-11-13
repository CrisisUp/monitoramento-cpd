#!/usr/bin/env bash
set -euo pipefail

BASE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE"

echo "============================================================"
echo "  SETUP — monitoramento-cpd"
echo "============================================================"

echo "[1/6] Verificando pré-requisitos..."
command -v docker >/dev/null 2>&1 || { echo "❌ Docker não encontrado."; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "❌ Docker Compose v2 não encontrado."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 não encontrado."; exit 1; }
echo "  ✅ Docker, Docker Compose e Python 3 encontrados."

echo "[2/6] Verificando .env..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "  ⚠️  .env criado a partir do .env.example."
  echo "  ⚠️  EDITE O .env ANTES DE CONTINUAR (senhas do Postgres e do Grafana)."
  echo "  ⚠️  Depois, rode 'make setup' novamente."
  exit 0
else
  echo "  ✅ .env já existe."
fi

echo "[3/6] Subindo a stack Docker..."
docker compose up -d
echo "  ✅ Stack iniciada."

echo "[4/6] Aguardando serviços ficarem saudáveis..."
for i in $(seq 1 30); do
  healthy=$(docker compose ps --format '{{.Health}}' 2>/dev/null | grep -c 'healthy' || true)
  running=$(docker compose ps --format '{{.State}}' 2>/dev/null | grep -c 'running' || true)
  if [ "$healthy" -ge 2 ] && [ "$running" -ge 5 ]; then
    echo "  ✅ $running serviços rodando ($healthy saudáveis)."
    break
  fi
  echo "  ... aguardando ($i/30) — $running rodando, $healthy saudáveis"
  sleep 3
done

echo "[5/6] Configurando ambiente Python..."
if [ ! -d .venv ]; then
  python3 -m venv .venv
  echo "  ✅ .venv criado."
fi
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet requests python-dotenv
echo "  ✅ Dependências instaladas."

echo "[6/6] Configurando o Zabbix via IaC..."
python configurar_zabbix.py

echo ""
echo "============================================================"
echo "  ✅ SETUP CONCLUÍDO!"
echo "============================================================"
echo ""
echo "  Próximos passos:"
echo "    make up        # (re)sobe a stack"
echo "    make ps        # vê o estado dos containers"
echo "    make health    # verifica saúde de todos os serviços"
echo "    make reset     # apaga volumes e recomeça do zero"
echo ""
echo "  Interfaces:"
echo "    Zabbix:  http://localhost:8080 (Admin/zabbix)"
echo "    Grafana: http://localhost:3000 (admin/senha do .env)"
echo ""
