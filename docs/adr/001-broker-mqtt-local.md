# ADR-001: Usar Mosquitto local em vez de broker público

- **Status:** Aceito
- **Data:** 2026-11-12
- **Autores:** Cristiano
- **Contexto do projeto:** Fatia 0 (Base Docker)

## Contexto

O firmware do ESP32 (no Wokwi) publica dados via MQTT. Para o Zabbix conseguir
ler esses dados, precisa haver um broker MQTT acessível.

As opções eram:

1. **Broker público** (`broker.emqx.io`): o que o firmware já usava.
2. **Broker local** (Mosquitto em Docker): na rede `cpd-net`.
3. **Híbrido** (ponte entre os dois).

O projeto precisa ser **reproduzível** e **isolado** (não expor dados do CPD
a terceiros).

## Decisão

Usar um **Mosquitto local** em Docker (`cpd-mosquitto`), na rede `cpd-net`.
O firmware continua publicando no broker público (por causa do Wokwi), mas
o Mosquitto local **puxa** esses dados via **bridge MQTT** (ver ADR-002).

## Consequências

### Positivas
- **Isolamento:** o Zabbix só vê o Mosquitto local, não o broker público.
- **Reprodutibilidade:** `docker compose up -d` sobe o broker junto com a stack.
- **Latência controlada:** o Mosquitto local está na mesma rede Docker do Zabbix.
- **Migração futura:** quando o hardware real entrar, basta apontar o firmware
  para o Mosquitto local e desligar a bridge.

### Negativas
- **Um serviço a mais** no `docker-compose.yml` (mais um ponto de falha).
- **Configuração extra** (o `mosquitto.conf` precisa de `include_dir`).
- **Chown read-only** nos logs do container (cosmético, mas confunde).

### Neutras
- O broker local usa **anônimo** por enquanto (aceitável em laboratório).
- O `log_type notice` enche os logs, mas é útil para debug.

## Alternativas descartadas

### A) Usar só o broker público
- **O que era:** o Zabbix leria direto do `broker.emqx.io`.
- **Por que foi descartada:** expõe dados do CPD a terceiros; latência
  variável; o broker público pode cair a qualquer momento.

### B) Usar só o broker local (sem bridge)
- **O que era:** o firmware publicaria direto no Mosquitto local.
- **Por que foi descartada:** o Wokwi não alcança `localhost`. O hardware
  real até poderia, mas nesta fase o Wokwi é obrigatório.

### C) Fazer polling HTTP do ESP32 direto
- **O que era:** o Zabbix faria `http://IP-do-ESP32/status` a cada 30s.
- **Por que foi descartada:** o Wokwi não expõe HTTP; o firmware MQTT já
  está maduro; o polling HTTP exigiria reescrever o firmware.

## Referências

- `docker-compose.yml` (serviço `mosquitto`)
- `mosquitto/config/mosquitto.conf`
- `docs/03.txt` (batalha dos 4 erros do Mosquitto 2.x)
