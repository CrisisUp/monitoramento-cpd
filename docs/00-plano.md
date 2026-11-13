# Plano de Projeto — Monitoramento CPD

**Versão:** 1.1
**Última atualização:** 2026-11-12
**Responsável:** Cristiano
**Status:** Em andamento (Fatia 1 concluída, Fatia 2 em preparação)

---

## 1. Contexto

Laboratório de monitoramento de sala de servidores (CPD) que combina:

- **Monitoramento físico:** um ESP32 (firmware RackMonitor v8.3) lê sensores de
  porta, presença, luminosidade, distância, temperatura e umidade, e publica
  o estado em tópicos MQTT.
- **Monitoramento lógico:** um Zabbix central coleta, avalia gatilhos, dispara
  alertas e expõe uma API.
- **Visualização:** um Grafana apresenta dashboards operacionais.

O objetivo é reproduzir, em ambiente próprio, a arquitetura do projeto de
referência "Monitoramento lógico e físico de sala de servidores", adaptando
o firmware existente (monolítico, MQTT + HMAC) sem reescrevê-lo.

### 1.1 Referência

Projeto original: monitoramento lógico + físico com ESP32, Zabbix, Grafana e
painel NOC 3D. Documentação estruturada em `README.md` do repositório de
origem.

### 1.2 Escopo do laboratório

- **Ambiente:** macOS Apple Silicon (Mac mini M4), Docker Desktop.
- **Orquestração:** Docker Compose (single-host).
- **Firmware:** simulado no Wokwi nesta fase; hardware real em fase posterior.
- **Rede:** local, sem exposição à internet.

---

## 2. Arquitetura

```text

┌──────────────┐ MQTT (TLS opcional) ┌────────────────────┐
│ ESP32 │ ──────────────────────▶ │ broker público │
│ (Wokwi ou │ tópicos: │ broker.emqx.io │
│ hardware) │ rack_monitor_... └─────────┬──────────┘
└──────────────┘ │ bridge MQTT
▼
┌────────────────────┐
│ Mosquitto local │
│ (Docker, cpd-net) │
│ tópicos: │
│ publico/... │
└─────────┬──────────┘
│ MQTT agent
▼
┌────────────────────┐
│ Zabbix Server │
│ (coleta + alerta) │
└─────────┬──────────┘
│ API
▼
┌────────────────────┐
│ Grafana │
│ (dashboards) │
└────────────────────┘
```

### 2.1 Fluxo de dados

1. O ESP32 publica em `rack_monitor_ABCD1234/{status,ambiente,heartbeat,...}`
   no broker público (`broker.emqx.io`).
2. O Mosquitto local, via **bridge MQTT**, assina esses tópicos no broker
   público e **republica localmente** com prefixo `publico/`.
3. O Zabbix Server lê os tópicos locais via **MQTT agent** (item type nativo
   do Zabbix 7.0), extrai campos com JSONPath e cria itens dependentes.
4. Gatilhos avaliam os itens e disparam alertas (Telegram, na Fatia 3).
5. O Grafana consulta a API do Zabbix e monta os dashboards.

### 2.2 Por que bridge e não conexão direta?

O Wokwi simula um ESP32 na nuvem e **não alcança `localhost`**. O firmware
já publica no broker público; a bridge puxa esses dados para dentro da rede
Docker, mantendo o Zabbix isolado da internet. Quando o hardware real entrar,
basta apontar o firmware para o Mosquitto local e desligar a bridge.

---

## 3. Decisões arquiteturais

| ID | Decisão | Justificativa | Alternativas descartadas |
| --- | --- | --- | --- |
| D1 | Broker MQTT local (Mosquitto em Docker) | Isolamento, reprodutibilidade, sem dependência de broker público | Usar apenas broker público (sem controle, latência variável) |
| D2 | Ingestão no Zabbix via **MQTT agent** | Item type nativo, reaproveita o JSON do firmware, sem recompilar | Zabbix sender (exigiria alterar firmware), HTTP polling (exigiria endpoint HTTP no firmware) |
| D3 | Bridge MQTT enquanto durar o Wokwi | Wokwi não alcança localhost | Expor Mosquitto local à internet (inseguro) |
| D4 | Ações (HMAC + botões) na última fatia | Isolar o mais crítico para o fim, com base estável | Implementar cedo (arriscado, muda muito) |
| D5 | Configuração idempotente via API (Fatia 5) | Reprodutibilidade, versionamento, sem cliques manuais | Configuração manual (não reproduzível) |
| D6 | Wokwi antes de hardware | Validar pipeline sem custo/risco de hardware | Hardware direto (maior custo de erro) |

---

## 4. Roadmap (fatias)

Cada fatia tem entregável, critério de aceite e dependências explícitas.

### Fatia 0 — Base Docker ✅

**Entregável:** stack Docker Compose com Mosquitto, Postgres, Zabbix Server,
Zabbix Web e Grafana; `.env` para segredos; volumes nomeados para persistência.

**Critério de aceite:**

- [x] `docker compose ps` mostra todos os serviços `Up` (2 `healthy`)
- [x] Broker responde a `mosquitto_pub`/`mosquitto_sub` local
- [x] Zabbix Web acessível em `localhost:8080`
- [x] Grafana acessível em `localhost:3000`

**Dependências:** nenhuma.

---

### Fatia 1 — Ponte MQTT (Wokwi → broker público → Mosquitto local) ✅

**Entregável:** `bridge.conf` no Mosquitto local, assinando os tópicos do
broker público e republicando com prefixo `publico/`.

**Critério de aceite:**

- [x] `mosquitto_sub` local em `publico/#` recebe `status`, `ambiente` e `heartbeat`
- [x] Ponte carrega sem erro de sintaxe
- [x] Heartbeat incrementa `uptime_s` a cada 30 s

**Dependências:** Fatia 0.

**Lições aprendidas:** ver seção 6.

---

### Fatia 2 — Ingestão no Zabbix (MQTT agent)

**Entregável:** host `esp32-cpd` no Zabbix, com 3 itens mestre (status,
ambiente, heartbeat) e itens dependentes com JSONPath; validação em
*Monitoring → Latest data*.

**Critério de aceite (a definir em detalhe na execução):**

- [ ] Item mestre `mqtt.status` retorna valor JSON não vazio
- [ ] Dependentes `temp_c`, `umid_pct`, `porta`, `modo`, `estado` populados
- [ ] Item `heartbeat.uptime_s` incrementa a cada 30 s
- [ ] `zabbix-server` alcança `cpd-mosquitto:1883` pela rede Docker

**Dependências:** Fatias 0 e 1.

---

### Fatia 3 — Gatilhos e Telegram

**Entregável:** triggers para temperatura, porta aberta, invasão
(`EMERGENCIA_RACK`), sensor DHT perdido e placa offline; ação de notificação
via Telegram.

**Critério de aceite:**

- [ ] Simular condição (ex.: porta aberta) dispara alerta no Telegram
- [ ] Alerta resolve automaticamente quando condição cessa
- [ ] Template de mensagem em português, com nome de exibição do host

**Dependências:** Fatia 2.

---

### Fatia 4 — Dashboard simples

**Entregável:** dashboard Grafana com painéis nativos (não 3D) mostrando
estado geral, temperatura/umidade, porta e contadores.

**Critério de aceite:**

- [ ] Dashboard atualiza a cada ≤ 30 s
- [ ] Estado reflete mudanças reais do Wokwi
- [ ] Provisionamento via arquivo (não cliques) já preparado para a Fatia 5

**Dependências:** Fatia 2.

---

### Fatia 5 — Configuração por código (idempotência)

**Entregável:** `zabbix/configurar.py` que cria/atualiza grupo, host,
template, macros, gatilhos e Telegram; executável repetidamente sem efeito
colateral. Exporta template YAML.

**Critério de aceite:**

- [ ] Rodar 1ª vez cria tudo
- [ ] Rodar 2ª vez não duplica, apenas atualiza
- [ ] Template exportado importável em Zabbix limpo
- [ ] Documentação: variáveis `.env` necessárias

**Dependências:** Fatias 2 e 3.

---

### Fatia 6 — NOC 3D

**Entregável:** dashboard Grafana customizado (painel único em tela cheia),
com sala/rack em 3D reagindo aos estados: `SEGURO`, `EMERGENCIA_RACK`,
`DESARMADO`, água, energia, porta, temperatura.

**Critério de aceite:**

- [ ] 3D reage ao estado sem recarregar página
- [ ] Clicar em problema foca o local correto
- [ ] Nada depende de internet (Three.js vendorizado)

**Dependências:** Fatias 4 e 5.

---

### Fatia 7 — Ações (HMAC)

**Entregável:** serviço Python `acoes.py` que confere sessão Grafana e
executa ações no Zabbix com usuário restrito (Reconhecer, Comentar,
Manutenção, Desarmar emergência, Reset contadores), assinando comandos com
a chave HMAC compartilhada com o firmware.

**Critério de aceite:**

- [ ] Botão no Grafana muda estado no ESP32 (via MQTT + HMAC)
- [ ] Auditoria em `docker compose logs acoes`
- [ ] Usuário sem permissão (Viewer) é bloqueado
- [ ] Nonce monotônico rejeita replay

**Dependências:** Fatias 1, 5.

---

## 5. Convenções

| Item | Convenção |
| --- | --- |
| Pasta do projeto | `~/Desktop/monitoramento-cpd` |
| Prefixo de containers | `cpd-` |
| Rede Docker | `cpd-net` |
| Prefixo de tópicos internos | `publico/` (bridge) |
| Nome técnico do host no Zabbix | `esp32-cpd` (sem interface de agente) |
| Nome de exibição no dashboard | `Rack CPD` |
| Segredos | `.env` (nunca versionado) |

---

## 6. Lições aprendidas

### Fatia 1 — Ponte MQTT

- **`include <arquivo>` não existe no Mosquitto 2.x.** Use `include_dir <pasta>`
  e coloque os arquivos em `conf.d/` com extensão `.conf`.
- **`remote_username`/`remote_password` vazios são erro fatal.** Para brokers
  anônimos, remova as linhas (não as deixe em branco).
- **`local_prefix` não existe como diretiva global.** O prefixo vai na própria
  linha `topic`: `topic <padrão> in <qos> <prefixo-local> <prefixo-remoto>`.
- **`chown: Read-only file system` nos logs é cosmético.** Vem do mount `:ro`
  do config; não afeta a operação. Para silenciar, mude para `:rw` (mas perde
  a proteção contra escrita acidental).
- **O mount `:ro` é bom.** Vale manter, e conviver com o aviso.

### Geral

- **Sempre valide o YAML antes do `up -d`:** `docker compose config --quiet`.
- **Logs com timestamps:** quando há múltiplos restarts, o timestamp UNIX na
  frente da linha identifica qual restart gerou o quê.
- **Prefixar tópicos com `publico/`** deixa óbvio o que veio de fora; útil
  quando o hardware real entrar e a bridge for desligada.

---

## 7. Riscos e mitigações

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| Broker público (`emqx.io`) instável | Fatia 1 falha intermitentemente | Bridge com `restart_timeout`; migrar hardware para broker local |
| Wokwi não alcança localhost | Ingestão direta impossível | Bridge MQTT (já implementada) |
| MAC do Wokwi vs. hardware real | Tópico muda (`ABCD1234`) | Parametrizar via `.env` e template |
| HMAC mal configurado na Fatia 7 | Ações recusadas ou replay aceito | Testes unitários no serviço Python + nonce monotônico |
| Docker Desktop no Mac dormindo | Containers pausam | Documentar `docker compose up -d` após acordar |

---

## 8. Referências

- Projeto original: README de "Monitoramento lógico e físico de sala de servidores"
- Firmware: `RackMonitor.ino` v8.3 (MQTT + HMAC + Nonce)
- Mosquitto: documentação oficial de bridge
- Zabbix 7.0 LTS: item type `MQTT agent`
