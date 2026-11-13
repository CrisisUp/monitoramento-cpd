#!/usr/bin/env bash
set -euo pipefail

BASE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE"

echo "============================================================"
echo "  HEALTH CHECK — monitoramento-cpd"
echo "============================================================"
echo ""
echo "Containers:"
docker compose ps

echo ""
echo "Testes rápidos:"
echo -n "  Mosquitto (ping broker): "
if docker compose exec -T mosquitto mosquitto_sub -h 127.0.0.1 -t '$SYS/broker/version' -C 1 -W 2 >/dev/null 2>&1; then
  echo "✅ OK"
else
  echo "❌ FALHOU"
fi

echo -n "  Zabbix Web (porta 8080): "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 | grep -q "200\|302"; then
  echo "✅ OK"
else
  echo "❌ FALHOU"
fi

echo -n "  Grafana (porta 3000): "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/health | grep -q "200"; then
  echo "✅ OK"
else
  echo "❌ FALHOU"
fi

echo -n "  NOC 3D (noc3d.html): "
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/public/grafana-custom/noc/noc3d.html | grep -q "200"; then
  echo "✅ OK"
else
  echo "❌ FALHOU"
fi

echo ""
