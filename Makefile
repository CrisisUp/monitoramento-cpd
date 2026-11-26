# ==============================================================================
# Makefile — Porta de entrada do monitoramento-cpd
# ==============================================================================

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Detecta automaticamente a virtualenv local (.venv) com fallback para python3 global
PYTHON := $(shell [ -x .venv/bin/python3 ] && echo .venv/bin/python3 || command -v python3)

# Comando multiplataforma para abrir URLs no navegador (macOS / Linux)
OPEN_CMD := $(shell command -v open 2>/dev/null || command -v xdg-open 2>/dev/null || echo echo)

# Parâmetros MQTT mTLS padrão do Rack CPD (sobrescrevíveis via CLI: make test-rack TEST_HIGH_TEMP=35.0)
MQTT_CONTAINER := cpd-mosquitto
MQTT_PORT      := 8883
MQTT_TOPIC     := elo5/esp32-rack-01/status

# Carrega variáveis do .env sem sobrescrever variáveis já definidas no ambiente/CLI
define LOAD_DOTENV
	@eval "$$($(PYTHON) -c 'import os, shlex; \
		p = ".env"; \
		lines = open(p, encoding="utf-8") if os.path.exists(p) else []; \
		pairs = []; \
		[pairs.append((k.strip(), v.strip().strip("\"").strip("\x27"))) \
		 for raw in lines \
		 for s in [raw.strip()] if s and not s.startswith("#") and "=" in s \
		 for k, v in [s.split("=", 1)]]; \
		[print(f"export {k}={shlex.quote(v)}") for k, v in pairs if k and k not in os.environ]')"
endef

.PHONY: help setup setup-triggers sync-triggers up down restart reset ps logs logs-z health backup \
        test-rack mqtt-restore mqtt-status \
        noc3d dashboard zabbix grafana shell shell-mqtt clean

help:
	@echo "========================================================================"
	@echo " monitoramento-cpd — Comandos Disponíveis"
	@echo "========================================================================"
	@echo " Ciclo de Vida da Stack:"
	@echo "  make setup          - Primeira vez: cria .env, sobe stack e roda IaC"
	@echo "  make sync-triggers  - Sincroniza macro {$TEMP.CRITICO} e triggers (25232, 25235, 25236) no Zabbix"
	@echo "  make up           - Sobe todos os containers em background"
	@echo "  make down         - Para a stack (mantém volumes persistentes)"
	@echo "  make restart      - Reinicia os containers da stack"
	@echo "  make reset        - Apaga volumes e recomeça do zero"
	@echo ""
	@echo " Diagnóstico & Observabilidade:"
	@echo "  make ps           - Mostra o estado dos containers"
	@echo "  make logs         - Acompanha logs de todos os serviços"
	@echo "  make logs-z       - Acompanha logs do zabbix-server"
	@echo "  make health       - Verifica saúde de todos os serviços"
	@echo "  make backup       - Gera backup do PostgreSQL e do Grafana"
	@echo ""
	@echo " Telemetria MQTT mTLS & Testes Ponta a Ponta:"
	@echo "  make test-rack    - Executa suíte E2E (Mosquitto mTLS 8883 + Zabbix 7.0)"
	@echo "  make mqtt-restore - Restaura payload baseline (23.4°C) no tópico retido"
	@echo "  make mqtt-status  - Lê a última mensagem retida no tópico do rack (mTLS)"
	@echo ""
	@echo " Acesso Rápido & Manutenção:"
	@echo "  make noc3d        - Abre o NOC 3D no navegador"
	@echo "  make dashboard    - Abre o dashboard 2D no navegador"
	@echo "  make zabbix       - Abre o frontend do Zabbix (porta 8080)"
	@echo "  make grafana      - Abre o frontend do Grafana (porta 3000)"
	@echo "  make shell        - Entra no shell do container zabbix-server"
	@echo "  make shell-mqtt   - Entra no shell do container $(MQTT_CONTAINER)"
	@echo "  make clean        - Remove caches Python e SQLs temporários"

# ------------------------------------------------------------------------------
# Ciclo de Vida da Stack
# ------------------------------------------------------------------------------
setup:
	@bash scripts/setup.sh
	@$(MAKE) setup-triggers

sync-triggers: setup-triggers

setup-triggers:
	$(LOAD_DOTENV) && \
	$(PYTHON) scripts/criar_triggers_rack.py

up:
	@docker compose up -d
	@echo "✅ Stack no ar. Use 'make ps' para ver o estado."

down:
	@docker compose down
	@echo "✅ Stack parada. Volumes preservados."

restart:
	@docker compose restart
	@echo "✅ Containers reiniciados."

reset:
	@bash scripts/reset.sh

# ------------------------------------------------------------------------------
# Diagnóstico & Backup
# ------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------
# Telemetria MQTT mTLS & Testes Ponta a Ponta
# ------------------------------------------------------------------------------
test-rack:
	$(LOAD_DOTENV) && \
	MQTT_CONTAINER="$(MQTT_CONTAINER)" \
	MQTT_PORT="8883" \
	MQTT_TOPIC="elo5/esp32-rack-01/status" \
	$(PYTHON) scripts/suite_testes_rack.py

mqtt-restore:
	@docker exec $(MQTT_CONTAINER) mosquitto_pub -h localhost -p $(MQTT_PORT) \
		--cafile /mosquitto/certs/ca.crt \
		--cert /mosquitto/certs/zabbix-client.crt \
		--key /mosquitto/certs/zabbix-client.key \
		-t "$(MQTT_TOPIC)" -r \
		-m '{"device_id":"esp32-rack-01","temp_c":23.4,"umid_pct":47.5,"porta":"FECHADA","modo":"ARMADO","estado":"NORMAL","dist_cm":85.0,"invasoes":0,"ambiente":"CPD_PRINCIPAL","luz":"CLARO","simulated":true}'
	@echo "✅ Baseline (23.4°C / FECHADA) restaurado em '$(MQTT_TOPIC)' via mTLS ($(MQTT_PORT))."

mqtt-status:
	@docker exec $(MQTT_CONTAINER) mosquitto_sub -h localhost -p $(MQTT_PORT) \
		--cafile /mosquitto/certs/ca.crt \
		--cert /mosquitto/certs/zabbix-client.crt \
		--key /mosquitto/certs/zabbix-client.key \
		-t "$(MQTT_TOPIC)" -C 1 -W 5

# ------------------------------------------------------------------------------
# Acesso Rápido & Manutenção
# ------------------------------------------------------------------------------
noc3d:
	@$(OPEN_CMD) "http://localhost:3000/public/grafana-custom/noc/noc3d.html"

dashboard:
	@$(OPEN_CMD) "http://localhost:3000/d/cpd-dashboard/cpd-dashboard"

zabbix:
	@$(OPEN_CMD) "http://localhost:8080"

grafana:
	@$(OPEN_CMD) "http://localhost:3000"

shell:
	@docker compose exec zabbix-server sh

shell-mqtt:
	@docker compose exec $(MQTT_CONTAINER) sh

clean:
	@find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true
	@rm -f backups/*.sql 2>/dev/null || true
	@echo "✅ Limpeza concluída (volumes preservados)."