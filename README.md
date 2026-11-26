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
