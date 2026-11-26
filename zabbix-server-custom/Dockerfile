FROM zabbix/zabbix-server-pgsql:alpine-7.0-latest

USER root

RUN apk add --no-cache mosquitto-clients

RUN cat <<'SCRIPT' > /usr/lib/zabbix/externalscripts/mqtt_status.sh
#!/bin/sh
TOPIC="${1:-elo5/esp32-rack-01/status}"
HOST="${2:-cpd-mosquitto}"
PORT="${3:-8883}"

CA_FILE="${MQTT_CA_FILE:-/etc/zabbix/certs/ca.crt}"
CERT_FILE="${MQTT_CERT_FILE:-/etc/zabbix/certs/zabbix-client.crt}"
KEY_FILE="${MQTT_KEY_FILE:-/etc/zabbix/certs/zabbix-client.key}"

for f in "$CA_FILE" "$CERT_FILE" "$KEY_FILE"; do
  if [ ! -r "$f" ]; then
    echo "Erro TLS: arquivo ausente ou sem leitura: $f" >&2
    exit 1
  fi
done

mosquitto_sub -h "$HOST" -p "$PORT" \
  --cafile "$CA_FILE" \
  --cert "$CERT_FILE" \
  --key "$KEY_FILE" \
  -t "$TOPIC" -C 1 -W 2
SCRIPT

RUN chmod 755 /usr/lib/zabbix/externalscripts/mqtt_status.sh && \
    chown zabbix:zabbix /usr/lib/zabbix/externalscripts/mqtt_status.sh

USER zabbix
