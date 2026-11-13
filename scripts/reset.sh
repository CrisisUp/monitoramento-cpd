#!/usr/bin/env bash
set -euo pipefail

BASE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE"

echo "============================================================"
echo "  ⚠️  RESET — APAGA TODOS OS DADOS"
echo "============================================================"
echo ""
echo "  Isso vai apagar:"
echo "    - Volumes do Postgres (dados do Zabbix)"
echo "    - Volumes do Grafana (dashboards editados na UI)"
echo "    - Volumes do Mosquitto (mensagens persistentes)"
echo ""
echo "  O código NÃO será apagado. Só os dados dos volumes."
echo ""
read -r -p "Tem certeza? Digite 'SIM' para confirmar: " resp

if [ "$resp" != "SIM" ]; then
  echo "Abortado."
  exit 0
fi

echo "→ Parando a stack e removendo volumes..."
docker compose down -v

echo "→ Subindo a stack novamente..."
docker compose up -d

echo "→ Aguardando serviços ficarem saudáveis..."
sleep 10

echo "→ Recriando a configuração do Zabbix..."
source .venv/bin/activate
python configurar_zabbix.py

echo ""
echo "✅ RESET CONCLUÍDO."
