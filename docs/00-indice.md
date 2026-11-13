# 📚 Índice dos Bastidores

A jornada completa do projeto está documentada em 12 arquivos.

| # | Arquivo | O que cobre |
|---|---|---|
| 01 | [01.txt](01.txt) | Fundação e decisões de arquitetura |
| 02 | [02.txt](02.txt) | Execução do Passo 0 (Mac + Docker) |
| 03 | [03.txt](03.txt) | Ponte MQTT (Mosquitto 2.x) |
| 04 | [04.txt](04.txt) | Zabbix + Dockerfile customizado + External check |
| 05 | [05.txt](05.txt) | Automação via Python (IaC do Zabbix) |
| 06 | [06.txt](06.txt) | Provisionamento do Grafana via JSON |
| 07 | [07.txt](07.txt) | UX/UI do Grafana (painéis e gradientes) |
| 08 | [08.txt](08.txt) | API do Zabbix 7.0 (idempotência, trends) |
| 09 | [09.txt](09.txt) | Vitória final do IaC (script idempotente) |
| 10 | [10.txt](10.txt) | Batalha final do Grafana (painel `table` para texto) |
| 11 | [11.txt](11.txt) | UX/UI profissional e níveis de "salvar" |
| 12 | [12.txt](12.txt) | NOC 3D: batalha do CSP e iframe |

## Como ler

- **Reproduzir o projeto:** leia `README.md` e depois 01 → 12.
- **Entender uma decisão:** procure o arquivo na tabela.
- **Contribuir:** leia `README.md`, `Makefile` e `docs/adr/` (quando existir).

## 🏛️ ADRs (Architecture Decision Records)

| # | ADR | Decisão |
|---|---|---|
| 000 | [template](adr/000-template.md) | Modelo para futuros ADRs |
| 001 | [broker-mqtt-local](adr/001-broker-mqtt-local.md) | Mosquitto local em vez de broker público |
| 002 | [bridge-mqtt](adr/002-bridge-mqtt.md) | Bridge MQTT em vez de conexão direta |
| 003 | [zabbix-via-api](adr/003-zabbix-via-api.md) | Zabbix via API (IaC) em vez de cliques |
| 004 | [3d-via-iframe](adr/004-3d-via-iframe.md) | NOC 3D via iframe em vez de plugin nativo |
| 005 | [grafana-via-json](adr/005-grafana-via-json.md) | Grafana via JSON em vez de cliques |
| 006 | [makefile](adr/006-makefile.md) | Makefile como porta de entrada |
