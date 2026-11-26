# Monitoramento CPD - Zabbix 7.0 + Mosquitto mTLS + Observabilidade

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

### Triggers Monitoradas no Zabbix (`esp32-rack-01`)

| ID | Finalidade | Condição / Observação |
| :--- | :--- | :--- |
| `25232` | Temperatura crítica | Disparo por limite de temperatura e recuperação ao normalizar |
| `25235` | Porta aberta | `last(/esp32-rack-01/esp32.porta)="ABERTA"` (reed switch / item `50760`) |
| `25236` | Invasão física | `last(/esp32-rack-01/esp32.invasoes)>0` (contador de invasões / item `50764`) |
