#!/usr/bin/env bash
set -euo pipefail

BASE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE"

DATA="$(date +%Y%m%d_%H%M%S)"
mkdir -p backups

echo "[1/2] Backup do Postgres (Zabbix)..."
docker compose exec -T postgres pg_dump -U zabbix -d zabbix > "backups/zabbix_${DATA}.sql"
echo "  ✅ backups/zabbix_${DATA}.sql"

echo "[2/2] Backup do Grafana (banco SQLite)..."
docker compose exec -T grafana tar -czf - /var/lib/grafana/grafana.db > "backups/grafana_${DATA}.tar.gz"
echo "  ✅ backups/grafana_${DATA}.tar.gz"

echo ""
echo "✅ Backups salvos em backups/"
