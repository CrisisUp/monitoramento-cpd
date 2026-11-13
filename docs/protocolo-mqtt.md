# 📡 Protocolo MQTT do Firmware RackMonitor v8.3

Este documento é o **contrato explícito** entre o firmware (ESP32) e o
consumidor (Zabbix, Grafana, NOC 3D). Qualquer mudança no firmware que
quebre este contrato deve ser **versionada** e documentada aqui.

**Versão do protocolo:** 1.0
**Versão do firmware:** 8.3
**Data:** 2026-11-12

---

## 🏗️ Arquitetura do fluxo

[ ESP32 ] ──publish──> [ broker público ] ──bridge──> [ Mosquitto local ] ──> [ Zabbix ] ──> [ Grafana ]
│ │
└──subscribe (comandos autenticados)──┘ │
│
[ NOC 3D (via API) ]

text

O ESP32 **publica** dados de sensores e **assina** comandos autenticados.
O Zabbix **lê** os dados via bridge MQTT. O Grafana **visualiza** via API do Zabbix.

---

## 📤 Tópicos publicados (ESP32 → broker)

### 1. `rack_monitor_ABCD1234/status`

**Payload:** JSON (ver [status-schema.json](../firmware/status-schema.json)).

**Frequência:** a cada 30s (polling) **e** em mudança de estado (push).

**Retained:** `true` (o broker guarda a última mensagem).

**Exemplo:**

```json
{
  "estado": "NORMAL",
  "modo": "ARMADO",
  "ts": "2026-11-12T13:46:47",
  "time_source": "RTC",
  "nonce": 0,
  "porta": false,
  "luz": true,
  "dist_cm": 335.9,
  "ativo": false,
  "ip": "10.10.0.2",
  "uid": "-",
  "acessos": 0,
  "invasoes": 0,
  "rearmes": 0,
  "alerta_temp": false,
  "critico_temp": false,
  "alerta_umid": false,
  "critico_umid": false,
  "taxa_temp_alerta": false,
  "ambiente": "OK",
  "temp_c": 24.0,
  "umid_pct": 40.0
}

Campos:

Campo	Tipo	Descrição
estado	string	NORMAL, AVISO SALA, APROXIMACAO RACK, EMERGENCIA RACK, INVASAO SALA, ACESSO RFID
modo	string	ARMADO ou DESARMADO
ts	string (ISO 8601)	Timestamp do RTC (ou NTP, ou millis)
time_source	string	RTC, NTP ou MILLIS
nonce	number	Contador anti-replay (uint64)
porta	boolean	Porta aberta?
luz	boolean	Luz acesa?
dist_cm	number	Distância do ultrassônico (cm)
ativo	boolean	Alarme sonoro ativo?
ip	string	IP do ESP32
uid	string	Último cartão RFID lido
acessos	number	Contador de acessos válidos
invasoes	number	Contador de invasões
rearmes	number	Contador de rearmes bloqueados
alerta_temp	boolean	Temperatura acima do limiar de alerta?
critico_temp	boolean	Temperatura acima do limiar crítico?
alerta_umid	boolean	Umidade acima do limiar de alerta?
critico_umid	boolean	Umidade acima do limiar crítico?
taxa_temp_alerta	boolean	Taxa de subida de temperatura acima do limite?
ambiente	string	OK, ALERTA ou CRITICO
temp_c	number	Temperatura (°C)
umid_pct	number	Umidade (%)
2. rack_monitor_ABCD1234/ambiente
Payload: JSON (subconjunto do status).

Frequência: a cada 30s.

Retained: true.

Exemplo:

json
{
  "ts": "2026-11-12T13:46:47",
  "time_source": "RTC",
  "temp_c": 24.0,
  "umid_pct": 40.0,
  "estado": "OK",
  "alerta_temp": false,
  "critico_temp": false,
  "alerta_umid": false,
  "critico_umid": false,
  "taxa_temp_alerta": false,
  "sensor_dht_ok": true,
  "limiares": {
    "t_alert": 30.0,
    "t_crit": 35.0,
    "u_alert": 65.0,
    "u_crit": 80.0
  }
}
Diferenças em relação ao status:

Inclui sensor_dht_ok (boolean).

Inclui limiares (objeto com os limites configurados).

Não inclui porta, luz, dist_cm, uid, contadores.

3. rack_monitor_ABCD1234/heartbeat
Payload: JSON.

Frequência: a cada 30s.

Retained: false (heartbeat é descartável).

Exemplo:

json
{
  "ts": "2026-11-12T13:47:43",
  "uptime_s": 30,
  "time_source": "RTC",
  "nonce": 0
}
Campos:

Campo	Tipo	Descrição
ts	string	Timestamp
uptime_s	number	Tempo ligado (segundos)
time_source	string	RTC, NTP ou MILLIS
nonce	number	Contador anti-replay
Uso: o Zabbix usa o heartbeat para detectar se o ESP32 está vivo
(gatilho nodata).

4. rack_monitor_ABCD1234/status/lwt
Payload: JSON (Last Will and Testament).

Frequência: publicada pelo broker quando o ESP32 desconecta
inesperadamente.

Retained: true.

Exemplo (online):

json
{"status": "online"}
Exemplo (offline):

json
{"status": "offline"}
5. rack_monitor_ABCD1234/logs
Payload: JSON (log de eventos).

Frequência: a cada evento (mudança de estado, RFID, porta, etc.).

Retained: false.

Exemplo:

json
{
  "ts": "12/11 13:46:47",
  "msg": "Estado: NORMAL -> AVISO SALA"
}
6. rack_monitor_ABCD1234/resposta
Payload: JSON (resposta a comandos autenticados).

Frequência: a cada comando processado.

Retained: false.

Exemplo:

json
{
  "seq": 42,
  "cmd": "DESARMAR",
  "ok": 1,
  "detalhe": "Desarmado remoto.",
  "nonce": 15
}
📥 Tópicos assinados (broker → ESP32)
1. rack_monitor_ABCD1234/comando
Payload: string (comando autenticado).

Formato:

text
COMANDO|TS|NONCE|SIG
RESET|TS|NONCE|SIG|rack2026
DESARMAR_EMERGENCIA|TS|NONCE|SIG|rack2026emg
COMANDO: ARMAR, DESARMAR, STATUS, TESTE, PANICO.

TS: timestamp Unix (informativo).

NONCE: contador monotônico (deve ser maior que o último).

SIG: HMAC-SHA256(COMANDO|TS|NONCE, chave_hmac).hex().toUpperCase().

Detalhes: ver comandos-schema.md.

2. rack_monitor_ABCD1234/comando/ambiente
Payload: string (comando de ambiente).

Formatos:

SET_TEMP_ALERTA <valor>

SET_TEMP_CRIT <valor>

SET_UMID_ALERTA <valor>

SET_UMID_CRIT <valor>

PANICO

STATUS_AMB

Sem autenticação HMAC (comandos de configuração de limiares).

🔒 Garantias de segurança
Garantia	Como é implementada
Autenticação	HMAC-SHA256 nos comandos (tópico /comando)
Anti-replay	Nonce monotônico persistido em NVS
Integridade	HMAC cobre COMANDO|TS|NONCE
Confidencialidade	❌ Não implementada (MQTT sem TLS no laboratório)
Token extra	RESET e DESARMAR_EMERGENCIA exigem token adicional
📊 Limiares configuráveis
O firmware aceita comandos SET_* para ajustar limiares em tempo real:

Comando	Faixa válida	Padrão
SET_TEMP_ALERTA <v>	15–50 °C	30 °C
SET_TEMP_CRIT <v>	20–60 °C	35 °C
SET_UMID_ALERTA <v>	30–90 %	65 %
SET_UMID_CRIT <v>	40–100 %	80 %
🎯 Como o Zabbix consome
Item	Tópico	JSONPath
esp32.temp	publico/.../status	$.temp_c
esp32.umid	publico/.../status	$.umid_pct
esp32.porta	publico/.../status	$.porta
esp32.modo	publico/.../status	$.modo
esp32.estado	publico/.../status	$.estado
esp32.distancia	publico/.../status	$.dist_cm
esp32.invasoes	publico/.../status	$.invasoes
esp32.ambiente	publico/.../status	$.ambiente
esp32.luz	publico/.../status	$.luz
O prefixo publico/ vem da bridge MQTT (ver ADR-002).

🔄 Versionamento
Quando o firmware mudar de forma incompatível (novo campo obrigatório,
mudança de nome, etc.), a versão do protocolo deve subir:

1.0 (atual): firmware 8.3.

1.1: adições compatíveis (novos campos opcionais).

2.0: mudanças incompatíveis (renomear campos, remover campos, mudar tipos).

O consumidor (Zabbix, NOC 3D) deve validar a versão antes de processar.

📚 Referências
status-schema.json — JSON Schema do status.

comandos-schema.md — comandos autenticados.

ADR-001 — decisão do broker local.

ADR-002 — decisão da bridge MQTT.

firmware/src/main.cpp — código do firmware.

text

Salve: `Ctrl+O`, `Enter`, `Ctrl+X`.

---

## 🛠️ Passo 3 — Criar `firmware/status-schema.json`

Este é o **JSON Schema** que valida o payload do `status`.

```bash
nano ~/Desktop/monitoramento-cpd/firmware/status-schema.json
Cole:

json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://github.com/CrisisUp/monitoramento-cpd/firmware/status-schema.json",
  "title": "RackMonitor Status",
  "description": "Schema do payload do tópico rack_monitor_ABCD1234/status",
  "version": "1.0",
  "type": "object",
  "required": [
    "estado", "modo", "ts", "time_source", "nonce",
    "porta", "luz", "dist_cm", "ativo", "ip",
    "acessos", "invasoes", "rearmes",
    "alerta_temp", "critico_temp", "alerta_umid", "critico_umid",
    "taxa_temp_alerta", "ambiente", "temp_c", "umid_pct"
  ],
  "properties": {
    "estado": {
      "type": "string",
      "enum": ["NORMAL", "AVISO SALA", "APROXIMACAO RACK", "EMERGENCIA RACK", "INVASAO SALA", "ACESSO RFID"]
    },
    "modo": {
      "type": "string",
      "enum": ["ARMADO", "DESARMADO"]
    },
    "ts": {
      "type": "string",
      "format": "date-time",
      "description": "Timestamp ISO 8601"
    },
    "time_source": {
      "type": "string",
      "enum": ["RTC", "NTP", "MILLIS"]
    },
    "nonce": {
      "type": "integer",
      "minimum": 0,
      "description": "Contador anti-replay (uint64)"
    },
    "porta": {
      "type": "boolean"
    },
    "luz": {
      "type": "boolean"
    },
    "dist_cm": {
      "type": "number",
      "minimum": -1,
      "description": "Distância em cm (-1 = sem leitura)"
    },
    "ativo": {
      "type": "boolean"
    },
    "ip": {
      "type": "string",
      "format": "ipv4"
    },
    "uid": {
      "type": "string",
      "description": "Último UID de cartão RFID (- = nenhum)"
    },
    "acessos": {
      "type": "integer",
      "minimum": 0
    },
    "invasoes": {
      "type": "integer",
      "minimum": 0
    },
    "rearmes": {
      "type": "integer",
      "minimum": 0
    },
    "alerta_temp": {
      "type": "boolean"
    },
    "critico_temp": {
      "type": "boolean"
    },
    "alerta_umid": {
      "type": "boolean"
    },
    "critico_umid": {
      "type": "boolean"
    },
    "taxa_temp_alerta": {
      "type": "boolean"
    },
    "ambiente": {
      "type": "string",
      "enum": ["OK", "ALERTA", "CRITICO"]
    },
    "temp_c": {
      "type": "number",
      "minimum": -50,
      "maximum": 100
    },
    "umid_pct": {
      "type": "number",
      "minimum": 0,
      "maximum": 100
    }
  },
  "additionalProperties": false
}
Salve.

🛠️ Passo 4 — Criar firmware/comandos-schema.md
bash
nano ~/Desktop/monitoramento-cpd/firmware/comandos-schema.md
Cole:

markdown
# 🔐 Comandos Autenticados do Firmware RackMonitor v8.3

Este documento descreve o formato dos comandos autenticados que o
firmware aceita no tópico `rack_monitor_ABCD1234/comando`.

**Versão do protocolo:** 1.0
**Versão do firmware:** 8.3

---

## Formato geral
COMANDO|TS|NONCE|SIG

text

| Campo | Tipo | Descrição |
|---|---|---|
| `COMANDO` | string | Nome do comando (case-sensitive, MAIÚSCULO) |
| `TS` | number | Timestamp Unix (segundos). Informativo, não validado. |
| `NONCE` | number | Contador monotônico (uint64). Deve ser **maior** que o último. |
| `SIG` | string | HMAC-SHA256(`COMANDO|TS|NONCE`, chave_hmac).hex().toUpperCase() |

**Exemplo:**
DESARMAR|1762964400|15|A1B2C3D4E5F6...

text

---

## Comandos disponíveis

### 1. `ARMAR`

**Formato:** `ARMAR|TS|NONCE|SIG`

**O que faz:** arma o vigilante (se a porta estiver fechada).

**Resposta (se OK):**
```json
{"seq": 1, "cmd": "ARMAR", "ok": 1, "detalhe": "Armado.", "nonce": 15}
Resposta (se a porta estiver aberta):

json
{"seq": 2, "cmd": "ARMAR", "ok": 0, "detalhe": "Bloqueado: porta aberta. Feche a porta.", "nonce": 15}
2. DESARMAR
Formato: DESARMAR|TS|NONCE|SIG

O que faz: desarma o vigilante (se a porta estiver fechada).

Bloqueio: se a porta estiver aberta, o comando é recusado. Use
DESARMAR_EMERGENCIA se precisar desarmar com a porta aberta.

3. DESARMAR_EMERGENCIA
Formato: DESARMAR_EMERGENCIA|TS|NONCE|SIG|rack2026emg

O que faz: desarma o vigilante mesmo com a porta aberta.
Exige token adicional (rack2026emg).

Uso: situações de emergência (manutenção, falha de sensor, etc.).

4. STATUS
Formato: STATUS|TS|NONCE|SIG

O que faz: força a publicação do status no tópico status.

Rate limit: 10 segundos entre comandos STATUS.

5. TESTE
Formato: TESTE|TS|NONCE|SIG

O que faz: executa o autodiagnóstico (buzzer, LED, sensores).

Resposta (se OK):

json
{"seq": 5, "cmd": "TESTE", "ok": 1, "detalhe": "Modo teste agendado.", "nonce": 15}
6. PANICO
Formato: PANICO|TS|NONCE|SIG

O que faz: dispara o alarme de pânico (simula invasão).

Bloqueio: se o sistema estiver DESARMADO, o comando é ignorado.

7. RESET
Formato: RESET|TS|NONCE|SIG|rack2026

O que faz: zera todos os contadores (acessos, invasões, etc.).
Exige token adicional (rack2026).

Como o consumidor (Python, Grafana) deve assinar
Exemplo em Python:

python
import hmac
import hashlib
import time

CHAVE_HMAC = "sua_chave_hmac_aqui"  # mesma chave do firmware (NVS)
NONCE_ATUAL = 15  # deve ser maior que o último

def assinar_comando(comando, nonce):
    ts = int(time.time())
    payload = f"{comando}|{ts}|{nonce}"
    sig = hmac.new(
        CHAVE_HMAC.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest().upper()
    return f"{comando}|{ts}|{nonce}|{sig}"

# Exemplo
comando = assinar_comando("DESARMAR", 16)
# "DESARMAR|1762964400|16|A1B2C3D4E5F6..."
Atenção: o NONCE deve ser persistido entre chamadas (não pode
repetir). Se o consumidor reiniciar, deve ler o último nonce de algum
lugar (banco, arquivo, etc.).

Garantias de segurança
Garantia	Como é implementada
Autenticação	HMAC-SHA256 (chave em NVS)
Anti-replay	Nonce monotônico persistido em NVS
Integridade	HMAC cobre COMANDO|TS|NONCE
Token extra	RESET e DESARMAR_EMERGENCIA exigem token adicional
Case-sensitive	O comando é comparado em maiúsculas, mas o HMAC usa o original
Comandos de ambiente (sem HMAC)
O tópico rack_monitor_ABCD1234/comando/ambiente aceita comandos de
configuração de limiares sem HMAC:

Comando	Faixa	Padrão
SET_TEMP_ALERTA <v>	15–50 °C	30 °C
SET_TEMP_CRIT <v>	20–60 °C	35 °C
SET_UMID_ALERTA <v>	30–90 %	65 %
SET_UMID_CRIT <v>	40–100 %	80 %
PANICO	—	—
STATUS_AMB	—	—
Por que sem HMAC? Esses comandos não mudam o estado de segurança
(armado/desarmado), só ajustam limiares. O risco é baixo.

Referências
protocolo-mqtt.md — protocolo completo.

firmware/src/main.cpp — código do firmware.

text

Salve.

---

## 🛠️ Passo 5 — Verificar a estrutura

```bash
cd ~/Desktop/monitoramento-cpd
ls -la docs/protocolo-mqtt.md firmware/status-schema.json firmware/comandos-schema.md
O que esperar: os 3 arquivos existem.

🛠️ Passo 6 — Validar o JSON Schema
Se você tiver o python3 com a biblioteca jsonschema, pode validar o schema:

bash
python3 -c "import json; json.load(open('firmware/status-schema.json')); print('✅ JSON válido')"
O que esperar: ✅ JSON válido.

🛠️ Passo 7 — Commit no GitHub
bash
cd ~/Desktop/monitoramento-cpd
git add docs/protocolo-mqtt.md firmware/
git status
O que verificar:

✅ docs/protocolo-mqtt.md

✅ firmware/status-schema.json

✅ firmware/comandos-schema.md

Se estiver OK:

bash
git commit -m "docs: adiciona contrato explícito do firmware (protocolo MQTT)

- docs/protocolo-mqtt.md: documenta todos os tópicos, payloads e garantias
- firmware/status-schema.json: JSON Schema do payload do status
- firmware/comandos-schema.md: comandos autenticados (HMAC + nonce)

Isso responde ao item 6 da lista de melhorias (contrato do firmware)."
git push
🎯 Resultado
Agora o projeto tem um contrato explícito:

Arquivo	Quem usa
docs/protocolo-mqtt.md	Quem vai integrar outro firmware
firmware/status-schema.json	Testes automatizados (#5)
firmware/comandos-schema.md	Quem vai implementar o serviço de ações (#7)
Itens resolvidos:

✅ 1. Makefile

✅ 3. Índice

✅ 4. ADRs

✅ 6. Contrato do firmware

✅ 8. Backup

Faltam: 2 (LICENSE), 5 (testes), 7 (NOC real), 9 (observabilidade), 10 (escalabilidade).
