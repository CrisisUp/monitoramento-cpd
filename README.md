# Monitoramento CPD - Zabbix 7.0 + Mosquitto mTLS + Observabilidade

[![Lint & Unit Tests](https://github.com/CrisisUp/monitoramento-cpd/actions/workflows/lint.yml/badge.svg?branch=main)](https://github.com/CrisisUp/monitoramento-cpd/actions/workflows/lint.yml)


> 📖 **História e Evolução Arquitetural:** Leia [docs/JORNADA.md](docs/JORNADA.md) para acompanhar a narrativa completa de como o projeto evoluiu de um único ESP32 na bancada até a observabilidade crítica com mTLS, IaC, CI/CD, Trigger Dependencies e SLA de 99.9%.
Stack de monitoramento, seguranca fisica e observabilidade para o CPD, integrada via ponte MQTT mTLS (:8883) a arquitetura distribuida do Elo5System2 (elo5-mosquitto nos topicos elo5/esp32-porta-01/status e elo5/esp32-rack-01/status).

## Arquitetura e Fluxo de Dados

- Nos ESP32 (esp32-porta-01 / esp32-rack-01) + ESP-NOW -> elo5-mosquitto (MQTT mTLS :8883)
- elo5-mosquitto -> cpd-mosquitto via Bridge mTLS (mosquitto/config/conf.d/bridge.conf) na rede elo5system2_elo5-net
- cpd-mosquitto -> Zabbix Server & Web 7.0 (mqtt_status.sh + JSONPath)
- Zabbix / Mosquitto -> Grafana + Prometheus + Exporters

## Comandos Principais

    cd ~/Desktop/monitoramento-cpd
    docker compose up -d mosquitto
    source .venv/bin/activate
    python configurar_zabbix.py
    python diag_zabbix.py
    pytest -v

### Automação de Triggers e Testes E2E (`Makefile`)

- `make setup-triggers` — Executa `scripts/criar_triggers_rack.py` para provisionar as triggers no host `esp32-rack-01`.
- `make test-rack` — Executa `scripts/suite_testes_rack.py` testando ingestão MQTT via mTLS (`8883`) e transições `PROBLEM` / `OK` no Zabbix `7.0`.
- `make mqtt-restore` — Restaura o payload baseline (`23.4°C`, `FECHADA`, `NORMAL`, `dist_cm: 85.0`, `invasoes: 0`) com flag retained (`-r`) no tópico `elo5/esp32-rack-01/status`.
- `make mqtt-status` — Consulta a última mensagem retida no tópico do rack via mTLS (`8883`).
- `make ci` — Pipeline completo: validação estática (`make lint`), sincronização IaC (`make sync-triggers`) e suíte E2E (`make test-rack`).
- `make report-last` — Exibe formatado no terminal o último relatório JSON de auditoria E2E (`reports/e2e_latest.json`).

#### Relatórios de Auditoria E2E (`reports/`)

Ao final de cada execução de `make test-rack` ou `make ci` (tanto em `PASS` quanto em `FAIL`), `scripts/suite_testes_rack.py` grava localmente (ignorados pelo Git via `.gitignore`):

- `reports/e2e_YYYYMMDD_HHMMSS.json` — histórico datado com status, duração, timestamps UTC, `eventid`s (`PROBLEM` e `OK`) e tempo de recuperação.
- `reports/e2e_latest.json` — cópia sempre atualizada da última rodada (`schema_version: "1.0"`).

```json
{
  "schema_version": "1.0",
  "host": "esp32-rack-01",
  "status": "PASS",
  "started_at_utc": "2026-11-26T12:22:00.120411+00:00",
  "finished_at_utc": "2026-11-26T12:22:18.842190+00:00",
  "duration_seconds": 18.72,
  "error": null,
  "summary": { "total_triggers": 3, "passed": 3, "failed": 0 },
  "triggers": [
    {
      "triggerid": "25232",
      "name": "Temperatura Crítica no Rack",
      "problem_eventid": "4182",
      "problem_timestamp_utc": "2026-11-26T12:22:03.000000+00:00",
      "ok_eventid": "4183",
      "ok_timestamp_utc": "2026-11-26T12:22:08.000000+00:00",
      "recovery_seconds": 5
    }
  ]
}
```

### Triggers Monitoradas no Zabbix (`esp32-rack-01`)

| ID | Finalidade | Condição / Observação |
| :--- | :--- | :--- |
| `25232` | Temperatura crítica | Disparo por limite de temperatura e recuperação ao normalizar |
| `25235` | Porta aberta | `last(/esp32-rack-01/esp32.porta)="ABERTA"` (reed switch / item `50760`) |
| `25236` | Invasão física | `last(/esp32-rack-01/esp32.invasoes)>0` (contador de invasões / item `50764`) |
