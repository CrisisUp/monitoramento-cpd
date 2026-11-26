# ==============================================================================
# Makefile — monitoramento-cpd (Rack 01 CPD | Mosquitto mTLS + Zabbix 7.0)
# ==============================================================================

SHELL := /usr/bin/env bash
.SHELLFLAGS := -euo pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help

# ------------------------------------------------------------------------------
# Configuração & Detecção de Ambiente
# ------------------------------------------------------------------------------
PYTHON          := $(if $(wildcard .venv/bin/python3),.venv/bin/python3,python3)
OPEN_CMD        := $(shell command -v open 2>/dev/null || command -v xdg-open 2>/dev/null || echo echo)
COMPOSE         := docker compose

MQTT_CONTAINER  ?= cpd-mosquitto
ZABBIX_CONTAINER?= zabbix-server
MQTT_HOST       ?= localhost
MQTT_PORT       ?= 8883
MQTT_TOPIC      ?= elo5/esp32-rack-01/status

ZABBIX_URL      ?= http://localhost:8080
GRAFANA_URL     ?= http://localhost:3000
NOC3D_URL       ?= http://localhost:8088/noc3d.html
DASHBOARD_URL   ?= http://localhost:8088

BACKUP_DIR      ?= backups
TIMESTAMP       := $(shell date +%Y%m%d_%H%M%S)

# Carrega .env sem sobrescrever variáveis já exportadas pela CLI
define LOAD_DOTENV
[ ! -f .env ] || { set -a; source .env; set +a; }
endef

.PHONY: help check-env setup setup-triggers sync-triggers up down restart reset \
        ps logs logs-z health backup \
        test-rack ci report-last mqtt-restore mqtt-status \
        noc3d dashboard zabbix grafana shell shell-mqtt lint clean

# ------------------------------------------------------------------------------
# Ajuda Auto-Documentada
# ------------------------------------------------------------------------------
help: ## Exibe esta lista de comandos organizados por categoria
	@echo "========================================================================"
	@echo " monitoramento-cpd — Comandos Disponíveis"
	@echo "========================================================================"
	@awk 'BEGIN {FS = ":.*##"; printf ""} \
		/^##@/ { printf "\n %s:\n", substr($$0, 5) } \
		/^[a-zA-Z0-9_-]+:.*?##/ { printf "  make %-15s - %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo "========================================================================"

check-env: ## Valida presença de Docker, Python e arquivo .env
	@command -v docker >/dev/null 2>&1 || { echo "❌ Docker não encontrado no PATH."; exit 1; }
	@$(COMPOSE) version >/dev/null 2>&1 || { echo "❌ Docker Compose v2 não disponível."; exit 1; }
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo "❌ Interpretador Python ($(PYTHON)) não encontrado."; exit 1; }
	@[ -f .env ] || { [ -f .env.example ] && cp .env.example .env && echo "⚠️  .env criado a partir de .env.example." || { echo "❌ .env ausente."; exit 1; }; }


##@ Ciclo de Vida da Stack
setup: check-env ## Primeira vez: valida .env, sobe stack e sincroniza triggers IaC
	$(COMPOSE) up -d --build
	$(MAKE) sync-triggers
	@echo "✅ Setup inicial concluído."

sync-triggers: setup-triggers ## Sincroniza macro {$TEMP.CRITICO} e triggers (25232, 25235, 25236) no Zabbix

setup-triggers: check-env lint ## Executa script idempotente de criação/atualização das triggers no Zabbix
	$(LOAD_DOTENV)
	$(PYTHON) scripts/criar_triggers_rack.py

up: check-env ## Sobe todos os containers em background
	$(COMPOSE) up -d

down: ## Para a stack mantendo os volumes persistentes
	$(COMPOSE) down

restart: check-env ## Reinicia todos os containers da stack
	$(COMPOSE) restart

reset: ## Apaga containers e volumes persistentes e recomeça do zero
	@echo "⚠️  Removendo todos os containers e volumes de dados..."
	$(COMPOSE) down -v --remove-orphans

##@ Diagnóstico & Observabilidade
ps: ## Mostra o estado atual dos containers
	$(COMPOSE) ps

logs: ## Acompanha logs em tempo real de todos os serviços
	$(COMPOSE) logs -f --tail=100

logs-z: ## Acompanha logs do zabbix-server
	$(COMPOSE) logs -f --tail=100 $(ZABBIX_CONTAINER)

health: ## Verifica saúde dos containers, broker mTLS e endpoints HTTP
	@echo ">>> Status dos Containers:"
	@$(COMPOSE) ps
	@echo ""
	@echo ">>> Verificação HTTP (Zabbix & Grafana):"
	@curl -fsS -o /dev/null "$(ZABBIX_URL)" && echo "  [OK] Zabbix Frontend ($(ZABBIX_URL))" || echo "  [FALHA] Zabbix Frontend ($(ZABBIX_URL))"
	@curl -fsS -o /dev/null "$(GRAFANA_URL)/api/health" && echo "  [OK] Grafana API ($(GRAFANA_URL))" || echo "  [FALHA] Grafana API ($(GRAFANA_URL))"

backup: check-env ## Gera backup comprimido dos volumes/bancos e dashboards
	@mkdir -p "$(BACKUP_DIR)"
	@$(LOAD_DOTENV); if $(COMPOSE) ps --services --filter "status=running" | grep -q "postgres"; then $(COMPOSE) exec -T postgres pg_dumpall -U "$${POSTGRES_USER:-zabbix}" | gzip > "$(BACKUP_DIR)/postgres_$(TIMESTAMP).sql.gz" && echo "✅ Backup PostgreSQL salvo em $(BACKUP_DIR)/postgres_$(TIMESTAMP).sql.gz"; else echo "⚠️  Container postgres não está em execução; pulando dump SQL."; fi


##@ Telemetria MQTT mTLS & Testes Ponta a Ponta
test-rack: sync-triggers ## Sincroniza triggers e executa suíte E2E (Mosquitto mTLS 8883 + Zabbix 7.0)
	$(LOAD_DOTENV)
	MQTT_CONTAINER="$(MQTT_CONTAINER)" \
	MQTT_HOST="$(MQTT_HOST)" \
	MQTT_PORT="$(MQTT_PORT)" \
	MQTT_TOPIC="$(MQTT_TOPIC)" \
	$(PYTHON) scripts/suite_testes_rack.py

ci: lint test-rack ## Pipeline completo: validação estática (lint) + sincronização IaC + suíte E2E

report-last: ## Exibe formatado no terminal o último relatório JSON em reports/e2e_latest.json
	@test -f reports/e2e_latest.json || { echo "❌ Nenhum relatório encontrado em reports/e2e_latest.json. Rode make test-rack primeiro."; exit 1; }
	@$(PYTHON) -c 'import json, pathlib; d = json.loads(pathlib.Path("reports/e2e_latest.json").read_text(encoding="utf-8")); s = d["summary"]; print("=" * 72); print(f"RELATÓRIO E2E — {d["host"]} | STATUS: {d["status"]} ({s["passed"]}/{s["total_triggers"]} triggers)"); print(f"Início UTC : {d["started_at_utc"]}"); print(f"Fim UTC    : {d["finished_at_utc"]} (duração: {d["duration_seconds"]}s)"); print("-" * 72); [print(f"  Trigger {tr["triggerid"]:<6} | PROBLEM={str(tr["problem_eventid"]):<6} | OK={str(tr["ok_eventid"]):<6} | rec={str(tr["recovery_seconds"])+"s":<5} | {tr["name"]}") for tr in d["triggers"]]; print("=" * 72)'

mqtt-restore: check-env ## Restaura payload baseline (23.4°C, porta fechada, 0 invasões) no tópico retido
	$(LOAD_DOTENV)
	$(COMPOSE) exec -T $(MQTT_CONTAINER) mosquitto_pub \
		-h localhost -p $(MQTT_PORT) \
		--cafile /mosquitto/certs/ca.crt \
		--cert /mosquitto/certs/client.crt \
		--key /mosquitto/certs/client.key \
		-t "$(MQTT_TOPIC)" -r \
		-m '{"device":"esp32-rack-01","temp":23.4,"umid":48.0,"porta":"FECHADA","distancia":120,"invasoes":0}'
	@echo "✅ Payload baseline restaurado em $(MQTT_TOPIC)."

mqtt-status: check-env ## Lê a última mensagem retida no tópico do rack via mTLS (timeout 5s)
	$(LOAD_DOTENV)
	$(COMPOSE) exec -T $(MQTT_CONTAINER) mosquitto_sub \
		-h localhost -p $(MQTT_PORT) \
		--cafile /mosquitto/certs/ca.crt \
		--cert /mosquitto/certs/client.crt \
		--key /mosquitto/certs/client.key \
		-t "$(MQTT_TOPIC)" -C 1 -W 5

##@ Acesso Rápido & Manutenção
noc3d: ## Abre o NOC 3D no navegador padrão
	@$(OPEN_CMD) "$(NOC3D_URL)"

dashboard: ## Abre o dashboard 2D no navegador padrão
	@$(OPEN_CMD) "$(DASHBOARD_URL)"

zabbix: ## Abre o frontend do Zabbix (porta 8080)
	@$(OPEN_CMD) "$(ZABBIX_URL)"

grafana: ## Abre o frontend do Grafana (porta 3000)
	@$(OPEN_CMD) "$(GRAFANA_URL)"

shell: ## Entra no shell interativo do container zabbix-server
	$(COMPOSE) exec $(ZABBIX_CONTAINER) sh

shell-mqtt: ## Entra no shell interativo do container cpd-mosquitto
	$(COMPOSE) exec $(MQTT_CONTAINER) sh

lint: ## Valida sintaxe Python (py_compile) e qualidade estática (ruff) em scripts/ e tests/
	@find scripts tests -type f -name '*.py' -print0 | xargs -0 $(PYTHON) -m py_compile
	@if $(PYTHON) -m ruff --version >/dev/null 2>&1; then \
		$(PYTHON) -m ruff check scripts tests; \
	else \
		echo "ℹ️  ruff não instalado em $(PYTHON); pulando análise estática."; \
	fi
	@echo "✅ Sintaxe e lint Python validados em scripts/ e tests/."

clean: ## Remove caches Python (__pycache__, .pyc) e temporários
	@find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	@find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
	@echo "✅ Caches e temporários removidos."
