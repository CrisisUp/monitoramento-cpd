# 🏢 Monitoramento CPD: Físico e Lógico (ESP32 + Zabbix + Grafana + Prometheus)

Sistema completo de monitoramento para sala de servidores (CPD) que une
**monitoramento físico** (sensores do ESP32) e **monitoramento lógico**
(coleta, alertas, visualização) num ecossistema reproduzível por código.

## 🚀 Início Rápido (1 minuto)

```bash
git clone https://github.com/CrisisUp/monitoramento-cpd.git
cd monitoramento-cpd
cp .env.example .env
# edite o .env (senhas do Postgres e Grafana)
make setup
```

Pronto! O projeto está no ar. Use make help para ver os comandos disponíveis.

## 📌 Arquitetura

```text
[ Wokwi (ESP32) ]
      │ MQTT (Internet)
      ▼
[ broker.emqx.io ]
      │ Bridge MQTT
      ▼
[ cpd-mosquitto ] (Docker - cpd-net)
      │ External Check (mqtt_status.sh)
      ▼
[ cpd-zabbix-server ] ──> [ cpd-postgres ]
      │ API
      ▼
[ cpd-grafana ] (2D + 3D + Observabilidade)
```

## Componentes

| Componente | Descrição / Papel |
| -- | -- |
| ESP32 (Wokwi) | Lê sensores (porta, presença, luz, distância, temperatura, umidade) e publica JSON via MQTT |
| Mosquitto local | Broker MQTT local com bridge para o broker público |
| Zabbix | Coleta, itens, gatilhos, macros, alertas |
| Grafana 2D | Dashboard com 5 painéis (Temperatura, Umidade, Modo, Estado, Histórico) |
| Grafana 3D | NOC com sala isométrica em Three.js |
| Prometheus | Observabilidade do pipeline (mensagens MQTT/s, CPU, memória) |

## 🎯 O que está funcionando

| Camada | O que foi construído | Status |
| -- | -- | -- |
| Base Docker | Mosquitto, Zabbix, Grafana, Postgres | ✅ |
| Ponte MQTT | Bridge do broker público para o local (prefixo publico/) | ✅ |
| Ingestão no Zabbix | Host esp32-cpd + 9 itens dependentes (JSONPath) | ✅ |
| Dashboard 2D | 5 painéis (Temperatura, Umidade, Modo, Estado, Histórico) | ✅ |
| NOC 3D | Sala isométrica com rack, porta, sensor, ar-condicionado | ✅ |
| Observabilidade | Prometheus + Grafana (mensagens MQTT/s, CPU, memória) | ✅ |
| Testes | 20 testes (schema do firmware + idempotência do IaC) | ✅ |
| IaC | Scripts Python idempotentes (Zabbix) + provisionamento (Grafana) | ✅ |
| Backup | Script para dump do Postgres e Grafana | ✅ |
| Escalabilidade | Guia para adicionar segunda sala/CPD | ✅ |
| Deploy Windows | Guia completo + script PowerShell | ✅ |
| ADRs | 8 decisões arquiteturais documentadas | ✅ |

LICENSE MIT ✅

## 🛠️ Pré-requisitos

- macOS (testado em Mac mini M4), Linux ou Windows 10/11.
- Docker Desktop instalado e rodando.
- Python 3 (para os scripts de IaC).
- Make (para rodar o Makefile).
- Wokwi (simulador online) ou ESP32 físico com o firmware RackMonitor v8.3.

## 🚀 Passo a Passo (Happy Path)

### 1. Preparar o Ambiente

```bash
git clone https://github.com/CrisisUp/monitoramento-cpd.git
cd monitoramento-cpd
cp .env.example .env
```

Edite o .env com suas senhas:

```env
POSTGRES_PASSWORD=umaSenhaForte
GRAFANA_ADMIN_PASSWORD=outraSenhaForte
```

### 2. Subir a Stack

```bash
make setup
```

O script setup.sh faz tudo:

- Verifica pré-requisitos.
- Cria o .env (se não existir).
- Sobe a stack Docker.
- Cria o venv Python e instala dependências.
- Configura o Zabbix via API (configurar_zabbix.py).

### 3. Acessar as Interfaces

| O quê | Endereço | Login |
| -- | -- | -- |
| Zabbix | http://localhost:8080 | Admin / zabbix |
| Grafana | http://localhost:3000 | admin / senha do .env |
| Dashboard 2D | http://localhost:3000/d/cpd-dashboard/cpd-dashboard | — |
| NOC 3D | http://localhost:3000/d/cpd-3d/cpd-3d | — |
| Observabilidade | http://localhost:3000/d/cpd-observabilidade/cpd-observabilidade | — |
| Prometheus | http://localhost:9090 | — |

### 4. Testar

```bash
make test       # 20 testes
make health     # verifica saúde de todos os serviços
```

## 📋 Comandos do dia a dia

| Para... | Comando |
| -- | -- |
| Subir tudo | make up |
| Parar tudo (mantém volumes) | make down |
| Apagar volumes e recomeçar | make reset |
| Ver estado | make ps |
| Ver logs | make logs |
| Ver logs do Zabbix | make logs-z |
| Backup | make backup |
| Abrir NOC 3D | make noc3d |
| Abrir Dashboard 2D | make dashboard |
| Abrir Zabbix | make zabbix |
| Abrir Grafana | make grafana |
| Abrir Observabilidade | make observabilidade |
| Rodar testes | make test |

## 📁 Estrutura de Pastas

```text
monitoramento-cpd/
├── Makefile                    # Porta de entrada única
├── README.md                   # Este arquivo
├── LICENSE                     # MIT
├── .env / .env.example         # Variáveis de ambiente
├── docker-compose.yml          # Stack Docker
├── configurar_zabbix.py        # IaC do Zabbix (idempotente)
├── configurar_telegram.py      # IaC do Telegram (futuro)
├── pytest.ini                  # Configuração dos testes
├── docs/
│   ├── 00-indice.md            # Índice navegável
│   ├── 00-plano.md             # Roadmap e decisões
│   ├── 01.txt ... 12.txt       # Bastidores da jornada
│   ├── README.configWindows.md # Guia de deploy no Windows
│   ├── como-adicionar-sala.md  # Guia de escalabilidade
│   ├── protocolo-mqtt.md       # Contrato do firmware
│   └── adr/                    # 8 ADRs (decisões arquiteturais)
├── firmware/
│   ├── status-schema.json      # JSON Schema do status
│   └── comandos-schema.md      # Comandos autenticados
├── grafana/
│   ├── config/grafana.ini
│   ├── dashboards/             # 3 dashboards (2D, 3D, Observabilidade)
│   ├── noc/                    # Cena 3D + vendor Three.js
│   └── provisioning/           # Datasources + dashboards
├── mosquitto/config/           # Broker local + bridge
├── prometheus/prometheus.yml   # Scrape targets
├── scripts/                    # setup.sh, reset.sh, health.sh, backup.sh
├── tests/                      # 20 testes
└── zabbix-server-custom/       # Dockerfile (mosquitto-clients + scripts)
```

## 🚑 Troubleshooting (Enciclopédia de Erros)

Esta seção documenta os problemas reais encontrados durante a construção
e suas soluções.

## Docker / Infraestrutura

| Sintoma | Causa | Solução |
| -- | -- | -- |
| zsh: event not found: ) | O zsh interpreta ! como histórico | Salve scripts em .sh e rode com bash arquivo.sh |
| port is already allocated | Outro serviço usa a porta | Mude o mapeamento (ex: "8081:8080") |
| cpd-postgres unhealthy | Senha com caractere especial | Coloque entre aspas: POSTGRES_PASSWORD="minha#senha" |

## Mosquitto (Bridge MQTT)

| Sintoma | Causa | Solução |
| -- | -- | -- |
| Unknown configuration variable "include" | Mosquitto 2.x usa include_dir | Use include_dir /mosquitto/config/conf.d |
| Empty bridge remote_username value | Diretivas vazias são erro fatal | Remova as linhas remote_username/remote_password |
| Unknown configuration variable "local_prefix" | Prefixo vai na linha topic | topic X in 1 publico/ "" |

## Zabbix

| Sintoma | Causa | Solução |
| -- | -- | -- |
| Loop: LogType "console" parameter can only be used with -f | command do compose sobrescreveu o entrypoint | Use Dockerfile customizado |
| SyntaxError: unterminated statement | Parser do Zabbix se confunde com - | Use External check com script .sh |
| Value of type "string" is not suitable for "Numeric" | JSONPath não configurado | Adicione Preprocessing com JSONPath |
| Invalid parameter "/1/trends": value must be 0 | Zabbix 7.0 rejeita trends > 0 em não-float | Use trends: "0" para texto/unsigned |
| unexpected parameter "hostid" | hostid é imutável no update | Remova do payload de update |

## Grafana (Dashboard 2D)

| Sintoma | Causa | Solução |
| -- | -- | -- |
| No data em todos os painéis | Datasource Zabbix sem UID correto | Verifique uid: zabbix no zabbix.yaml |
| No data em painéis de texto (Modo, Estado) | queryType: 0 (Metrics) em vez de 2 (Text) | Use queryType: "2" e tipo stat com Fields = All Fields |
| Painel Modo/Estado mostra No data | vizConfig.group: table com texto | Use stat com reduceOptions.fields: "/.*/" |

## Grafana (NOC 3D)

| Sintoma | Causa | Solução |
| -- | -- | -- |
| Iframe em branco | CSP do Grafana bloqueia iframes | Adicione allow_embedding = true no grafana.ini |
| Iframe em branco | Falta [panels] disable_sanitize_html | Adicione [panels] disable_sanitize_html = true |
| Fundo roxo | Canvas com tamanho 0 | Use width:100%; height:100vh no iframe |
| Failed to resolve module specifier "three" | Import de OrbitControls sem caminho local | Troque from 'three' por from '../../three.module.min.js' |

## Grafana (Observabilidade)

| Sintoma | Causa | Solução |
| -- | -- | -- |
| No data nos painéis | Datasource Prometheus não configurado | Crie prometheus.yaml com uid: prometheus |
| No data nos painéis | Nomes de métricas diferentes | Use broker_messages_* (Mosquitto) e container_* (cAdvisor) |
| cAdvisor não expõe CPU/memória | Limitação do macOS (Docker Desktop) | No Windows funciona 100% |

## Windows (Produção)

| Sintoma | Causa | Solução |
| -- | -- | -- |
| No data nos painéis | Datasource Prometheus não configurado | Crie prometheus.yaml com uid: prometheus |
| No data nos painéis | Nomes de métricas diferentes | Use broker_messages_* (Mosquitto) e container_* (cAdvisor) |
| cAdvisor não expõe CPU/memória | Limitação do macOS (Docker Desktop) | No Windows funciona 100% |

## 📚 Lições Aprendidas

Isolamento é tudo: Usar uma rede Docker (cpd-net) e um broker local evitou expor o Zabbix à internet, usando uma "ponte" (bridge MQTT) para puxar os dados.

Infraestrutura como Código (IaC): Criar os itens manualmente levaria 15 minutos e seria sujeito a erros. O script configurar_zabbix.py provou que a API do Zabbix é rápida, idempotente e à prova de erros.

O tipo External check é o "canivete suíço": Quando o Zabbix luta contra scripts shell, empacotar o comando em um .sh no container e chamá-lo via External Check é a solução mais robusta.

Dockerfile customizado: Sobrescrever entrypoint ou command de imagens oficiais é uma armadilha. A melhor prática é estender a imagem com um Dockerfile.

Grafana: table para texto: O painel stat só lida com números. Para texto, use table ou stat com Fields = All Fields.

Grafana: queryType correto: O plugin Zabbix usa "0" para Metrics (numérico) e "2" para Text (texto).

Grafana: provisionamento via JSON: O Grafana 13 lê dashboards em schema v2, não v1. O JSON no disco precisa estar no formato novo.

Grafana: allow_embedding + [panels] disable_sanitize_html: Para iframes funcionarem, são necessárias 4 configurações no grafana.ini.

Prometheus: nomes de métricas: O mosquitto-exporter usa broker_messages_*, não mosquitto_messages_*. O cAdvisor no macOS usa id=~"/docker/.*", não name=~"cpd-.*".

Testes: 20 testes garantem que o schema do firmware e a idempotência do IaC estão corretos. Sem eles, mudanças quebram silenciosamente.

## 🔮 Roadmap (o que falta)

☑ Base Docker
☑ Ponte MQTT
☑ Ingestão no Zabbix
□ Gatilhos e Telegram (Fatia 3 — adiada)
☑ Dashboard 2D
☑ Configuração via IaC (Zabbix)
☑ NOC 3D
☑ Ações HMAC (Fatia 7 — adiada)
☑ Observabilidade (Prometheus)
☑ Testes automatizados
☑ Contrato do firmware
☑ Backup / recuperação
☑ Escalabilidade
☑ Deploy Windows
☑ ADRs
☑ LICENSE
Falta apenas o Telegram (Fatia 3).

## 📚 Documentação Adicional

| Documento | O que contém |
| -- | -- |
| docs/00-indice.md | Índice navegável de toda a documentação |
| docs/00-plano.md | Roadmap e decisões |
| docs/01.txt a 12.txt | Bastidores da jornada (erros e acertos) |
| docs/adr/ | 8 ADRs (decisões arquiteturais) |
| docs/protocolo-mqtt.md | Contrato do firmware (tópicos, payloads) |
| docs/README.configWindows.md | Guia de deploy no Windows |
| docs/como-adicionar-sala.md | Guia de escalabilidade |

## 📄 Licença

Este projeto está licenciado sob a MIT License.
Veja o arquivo LICENSE para mais detalhes.

## 🙏 Agradecimentos

Projeto de referência: "Monitoramento lógico e físico de sala de servidores".

Comunidade Zabbix, Grafana, Mosquitto e Three.js.
