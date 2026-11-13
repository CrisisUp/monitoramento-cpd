# ============================================================
# Makefile — Porta de entrada do monitoramento-cpd
# ============================================================

.PHONY: help setup up down reset ps logs logs-z health backup noc3d dashboard zabbix grafana shell clean

help:
	@echo "Comandos disponíveis:"
	@echo "  make setup     - Primeira vez: cria .env, sobe stack, roda IaC"
	@echo "  make up        - Sobe a stack"
	@echo "  make down      - Para a stack (mantém volumes)"
	@echo "  make reset     - Apaga volumes e recomeça do zero"
	@echo "  make ps        - Vê o estado dos containers"
	@echo "  make logs      - Vê os logs (todos)"
	@echo "  make logs-z    - Vê os logs do Zabbix"
	@echo "  make health    - Verifica saúde de todos os serviços"
	@echo "  make backup    - Backup do Postgres e do Grafana"
	@echo "  make noc3d     - Abre o NOC 3D no navegador"
	@echo "  make dashboard - Abre o dashboard 2D no navegador"
	@echo "  make zabbix    - Abre o Zabbix no navegador"
	@echo "  make grafana   - Abre o Grafana no navegador"
	@echo "  make shell     - Entra no shell do container do Zabbix"
	@echo "  make clean     - Limpa arquivos temporários (mantém volumes)"

setup:
	@bash scripts/setup.sh

up:
	@docker compose up -d
	@echo "✅ Stack no ar. Use 'make ps' para ver o estado."

down:
	@docker compose down
	@echo "✅ Stack parada. Volumes preservados."

reset:
	@bash scripts/reset.sh

ps:
	@docker compose ps

logs:
	@docker compose logs -f

logs-z:
	@docker compose logs -f zabbix-server

health:
	@bash scripts/health.sh

backup:
	@bash scripts/backup.sh

noc3d:
	@open "http://localhost:3000/public/grafana-custom/noc/noc3d.html"

dashboard:
	@open "http://localhost:3000/d/cpd-dashboard/cpd-dashboard"

zabbix:
	@open "http://localhost:8080"

grafana:
	@open "http://localhost:3000"

shell:
	@docker compose exec zabbix-server sh

clean:
	@rm -rf .venv/__pycache__ **/__pycache__
	@rm -f backups/*.sql 2>/dev/null || true
	@echo "✅ Limpeza concluída (volumes preservados)."
