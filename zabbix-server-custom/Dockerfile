FROM zabbix/zabbix-server-pgsql:alpine-7.0-latest

USER root

# Instala o cliente MQTT
RUN apk add --no-cache mosquitto-clients

# Cria o script externo já com permissão de execução e dono zabbix
RUN echo '#!/bin/sh' > /usr/lib/zabbix/externalscripts/mqtt_status.sh && \
    echo 'mosquitto_sub -h cpd-mosquitto -t publico/rack_monitor_ABCD1234/status -C 1 -W 2' >> /usr/lib/zabbix/externalscripts/mqtt_status.sh && \
    chmod +x /usr/lib/zabbix/externalscripts/mqtt_status.sh && \
    chown zabbix:zabbix /usr/lib/zabbix/externalscripts/mqtt_status.sh

# Volta ao usuário padrão
USER zabbix