# ADR-002: Usar bridge MQTT em vez de conexão direta

- **Status:** Aceito
- **Data:** 2026-11-12
- **Autores:** Cristiano

## Contexto

O Wokwi não alcança localhost. O Mosquitto local precisa puxar os dados
do broker público.

## Decisão

Usar bridge MQTT no Mosquitto local (mosquitto/config/conf.d/bridge.conf).
Os tópicos do broker público são republicados localmente com prefixo
publico/.

## Consequências

### Positivas
- Isolamento: o Zabbix só vê dados com prefixo publico/.
- Migração transparente: quando o hardware real entrar, desliga a bridge.

### Negativas
- Dependência do broker público.
- Configuração extra (bridge.conf).

## Alternativas descartadas

### A) Expor o Mosquitto local à internet
- Inseguro e instável.

### B) Firmware publicar direto no local
- Impossível — o Wokwi não alcança localhost.

## Referências

- mosquitto/config/conf.d/bridge.conf
- docs/03.txt
