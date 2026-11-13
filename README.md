# Monitoramento CPD: Físico e Lógico com ESP32, Zabbix e MQTT

Este projeto implementa uma solução completa de monitoramento para uma sala de servidores (CPD). Ele une o **monitoramento físico** (sensores de temperatura, porta, presença) com o **monitoramento lógico** (coleta, processamento e alertas), usando um ecossistema moderno e conteinerizado.

## 📌 Arquitetura do Projeto

O fluxo de dados foi desenhado para ser isolado e reprodutível localmente:

1. **Dispositivo (ESP32/Wokwi):** Simula os sensores e publica um payload JSON em um broker público (`broker.emqx.io`).
2. **Ponte MQTT (Mosquitto Local):** Um container Mosquitto roda localmente, assina os tópicos do broker público e os republica internamente com o prefixo `publico/`.
3. **Banco de Dados e Orquestração (Zabbix):** O Zabbix Server (via script customizado) lê os tópicos do Mosquitto local. Ele extrai os dados individuais (JSONPath) e armazena no PostgreSQL.
4. **Visualização:** (Futuro) Grafana para dashboards e Zabbix Web para gestão de alertas.

## 🛠️ Pré-requisitos

- **macOS** (Apple Silicon) ou qualquer sistema com Docker.
- **Docker Desktop** instalado e em execução.
- **Python 3** e **Terminal** para rodar os scripts de configuração (IaC).
- **Conta no Telegram** (para receber os alertas).

---

## 🚀 Passo a Passo (Happy Path)

### 1. Preparar o Ambiente
Clone o repositório e crie o arquivo de variáveis de ambiente:
```bash
cp .env.example .env
Abra o .env e preencha as senhas do PostgreSQL, Grafana e, futuramente, o Token do Telegram.

2. Subir a Infraestrutura
bash
docker compose up -d
Aguarde até que todos os containers (cpd-mosquitto, cpd-postgres, cpd-zabbix-server, cpd-zabbix-web, cpd-grafana) estejam Up (healthy).

3. Configurar a Ponte MQTT (Mosquitto)
Para que o Zabbix local receba os dados do Wokwi sem expor sua rede, usamos uma ponte. O arquivo mosquitto/config/conf.d/bridge.conf já está configurado.
(Nota: O Mosquitto 2.x não aceita include, por isso usamos include_dir no arquivo principal).

4. Configurar o Zabbix via Infraestrutura como Código (IaC)
Não crie itens manualmente na interface. Use o script de automação.
Crie um ambiente virtual Python e instale as dependências:

bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests python-dotenv
Adicione as credenciais do Zabbix no .env (ZABBIX_URL, ZABBIX_USER, ZABBIX_PASSWORD).

Crie o Host e o Item Mestre (Ouvinte):
(Aqui entraria o script para criar o Host e o script externo)

Crie os Itens Dependentes:
O script configurar_zabbix.py já está pronto para ler o JSON e criar as métricas (Temperatura, Umidade, Porta, etc.).

bash
python configurar_zabbix.py
5. Verificar os Dados
Acesse http://localhost:8080 (Admin/zabbix). Vá em Monitoring → Latest data. Você verá a temperatura, umidade e estado da porta atualizando em tempo real.

🚑 Troubleshooting (Enciclopédia de Erros)
Este projeto foi construído superando desafios reais de ambiente macOS e Docker. Se você encontrar problemas, consulte a tabela abaixo.

Sintoma	Causa Provável	Solução
zsh: event not found: ) ao colar scripts no terminal do Mac.	O zsh interpreta o caractere ! como histórico.	Salve o comando em um arquivo .sh e execute com bash arquivo.sh, ou coloque a string entre aspas simples.
Mosquitto morre com Unknown configuration variable "include".	O Mosquitto 2.x substituiu include por include_dir.	Coloque os arquivos .conf na pasta conf.d/ e use include_dir /mosquitto/config/conf.d no arquivo principal.
Mosquitto morre com Empty bridge remote_username value.	Diretivas de autenticação vazias causam erro fatal.	Remova as linhas remote_username e remote_password do bridge.conf se o broker for anônimo.
Mosquitto morre com Unknown configuration variable "local_prefix".	A sintaxe da ponte foi alterada.	O prefixo deve ir na própria linha do tópico: topic topico/remoto in 1 publico/ "".
Zabbix Server entra em loop: ERROR: "LogType" "console" parameter can only be used with the -f.	O command do Docker Compose sobrescreveu o script de inicialização (entrypoint) do container.	Crie um Dockerfile customizado (zabbix-server-custom). Nele, instale o mosquitto-clients via apk e não sobrescreva o entrypoint original no Compose.
Item tipo Script do Zabbix dá SyntaxError: unterminated statement.	O parser interno do Zabbix se confunde com hífens (flags) de comandos shell.	Mude o item para o tipo External check e crie o script físico (mqtt_status.sh) dentro da pasta /usr/lib/zabbix/externalscripts/ do container, garantindo permissão de execução (chmod +x).
Item dependente dá erro: Value of type "string" is not suitable for value type "Numeric (float)".	O passo de Preprocessing (JSONPath) não foi adicionado ou está vazio.	Na aba Preprocessing do item, adicione o passo JSONPath com o caminho exato (ex: $.temp_c).
Item "Porta Aberta" dá erro no tipo numérico.	O JSON envia true/false (string) e o campo espera número.	Configure o tipo de informação do item como Character para receber a string, e a conversão será feita nos gatilhos.
📚 Lições Aprendidas (Para a posteridade)
Isolamento é tudo: Usar uma rede Docker (cpd-net) e um broker local evitou expor o Zabbix à internet, usando uma "ponte" para puxar os dados.

Infraestrutura como Código (IaC): Criar os 7 itens dependentes manualmente levaria 15 minutos. O script configurar_zabbix.py provou que a API do Zabbix é rápida e à prova de erros de digitação.

O tipo External check é o "canivete suíço": Quando o Zabbix luta contra scripts shell, empacotar o comando em um .sh no container e chamá-lo via External Check é a solução mais robusta.

text

---

### O que acha dessa estrutura?

Ela cobre a dor exata de quem está começando (os erros) e serve como manual de operação (o caminho feliz).

Se você aprovar, podemos:
1. **Salvar esse conteúdo no `README.md` agora.**
2. **Voltar para a Fatia 3 (Telegram)** e, no final de cada nova fatia, adicionar uma seção nova a este documento.

Me diga o que achou! Quer ajustar algum ponto antes de salvarmos?









# 🏢 Monitoramento CPD: Físico e Lógico (ESP32 + Zabbix + MQTT)

Este projeto implementa uma solução completa de monitoramento para uma sala de servidores (CPD). Ele une o **monitoramento físico** (sensores de temperatura, porta, presença, etc. em um ESP32) com o **monitoramento lógico** (coleta centralizada, processamento e alertas) usando um ecossistema moderno e conteinerizado.

## 📌 Visão Geral da Arquitetura

O fluxo de dados foi desenhado para ser isolado e reprodutível localmente, usando o Wokwi (simulador) como fonte de dados nesta fase.

1. **Dispositivo (ESP32/Wokwi):** Simula os sensores e publica um payload JSON em um broker público (`broker.emqx.io`).
2. **Ponte MQTT (Mosquitto Local):** Um container Mosquitto roda localmente, assina os tópicos do broker público e os republica internamente com o prefixo `publico/`.
3. **Banco de Dados e Orquestração (Zabbix):** O Zabbix Server (via script externo customizado) lê os tópicos do Mosquitto local. Ele extrai os dados individuais (JSONPath) e armazena no PostgreSQL.
4. **Visualização:** (Fase Futura) Grafana para dashboards e Zabbix Web para gestão de alertas.

**Diagrama do Fluxo:**
```text
[ Wokwi (ESP32) ]
      │ (MQTT - Internet)
      ▼
[ broker.emqx.io ]
      │ (Bridge MQTT)
      ▼
[ cpd-mosquitto ] (Docker - cpd-net)
      │ (External Check via script .sh)
      ▼
[ cpd-zabbix-server ] ──> [ cpd-postgres ]
      │ (API)
      ▼
[ cpd-grafana ] (Futuro)
🛠️ Pré-requisitos
Sistema Operacional: macOS (testado em Mac mini M4 Apple Silicon) ou Linux.

Docker Desktop instalado e em execução (com suporte a arm64 nativo).

Python 3 (para rodar scripts de automação IaC).

Wokwi (simulador online) configurado para rodar o firmware do ESP32 com os tópicos MQTT.

🚀 Passo a Passo (Happy Path)
1. Clonar e Preparar o Ambiente
bash
git clone <url-do-repositorio>
cd monitoramento-cpd
cp .env.example .env
Abra o .env e preencha as senhas do PostgreSQL e do Grafana.

⚠️ Atenção: Se a senha tiver caracteres especiais (#, $, !, espaço), coloque-a entre aspas duplas (ex: POSTGRES_PASSWORD="minha#senha").

2. Subir a Infraestrutura Base
bash
docker compose up -d
docker compose ps
Aguarde até que todos os containers (cpd-mosquitto, cpd-postgres, cpd-zabbix-server, cpd-zabbix-web, cpd-grafana) estejam Up (healthy). O Zabbix Web estará disponível em http://localhost:8080 (Admin/zabbix).

3. Configurar a Ponte MQTT (Mosquitto)
Para que o Zabbix local receba os dados do Wokwi sem expor sua rede, usamos uma bridge no Mosquitto.

O arquivo mosquitto/config/conf.d/bridge.conf já está configurado.

Certifique-se de que a linha include_dir /mosquitto/config/conf.d está ativa no mosquitto.conf.

Teste com o Wokwi rodando:

bash
docker compose exec mosquitto mosquitto_sub -h localhost -t 'publico/#' -v
4. Configurar o Zabbix via Infraestrutura como Código (IaC)
Não crie itens manualmente na interface. Use o script de automação para criar o Host, o Item Mestre e os 8 itens dependentes.

bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests python-dotenv
python configurar_zabbix.py
O script lerá o arquivo .env (adicione ZABBIX_URL, ZABBIX_USER, ZABBIX_PASSWORD nele) e criará toda a árvore de monitoramento de forma idempotente.

5. Verificar os Dados
Acesse http://localhost:8080 (Zabbix). Vá em Monitoring → Latest data, filtre pelo host esp32-cpd e veja os 9 itens (Temperatura, Umidade, Porta, etc.) atualizando em tempo real.

🚑 Troubleshooting (Enciclopédia de Erros)
Esta seção documenta os problemas reais encontrados durante a construção e suas soluções.

Sintoma / Erro	Causa Provável	Solução
zsh: event not found: ) ao colar scripts no terminal do Mac.	O zsh interpreta o caractere ! como histórico.	Salve o comando em um arquivo .sh e execute com bash arquivo.sh, ou use aspas simples.
Mosquitto morre com Unknown configuration variable "include".	O Mosquitto 2.x substituiu include por include_dir.	Coloque os arquivos .conf na pasta conf.d/ e use include_dir /mosquitto/config/conf.d no arquivo principal.
Mosquitto morre com Empty bridge remote_username value.	Diretivas de autenticação vazias causam erro fatal.	Remova as linhas remote_username e remote_password do bridge.conf se o broker for anônimo.
Mosquitto morre com Unknown configuration variable "local_prefix".	A sintaxe da ponte foi alterada no Mosquitto 2.x.	O prefixo deve ir na própria linha do tópico: topic topico/remoto in 1 publico/ "".
Zabbix Server entra em loop: ERROR: "LogType" "console" parameter can only be used with the -f.	O command do Docker Compose sobrescreveu o script de inicialização (entrypoint).	Crie um Dockerfile customizado (zabbix-server-custom). Instale o mosquitto-clients via apk e não sobrescreva o entrypoint original no Compose.
Item tipo Script do Zabbix dá SyntaxError: unterminated statement.	O parser interno do Zabbix se confunde com hífens (flags) de comandos shell.	Mude o item para o tipo External check e crie o script físico (mqtt_status.sh) dentro da pasta /usr/lib/zabbix/externalscripts/ do container, garantindo permissão de execução (chmod +x).
Item dependente dá erro: Value of type "string" is not suitable for value type "Numeric (float)".	O passo de Preprocessing (JSONPath) não foi adicionado ou está vazio.	Na aba Preprocessing do item, adicione o passo JSONPath com o caminho exato (ex: $.temp_c).
Item "Porta Aberta" dá erro no tipo numérico.	O JSON envia true/false (string) e o campo espera número.	Configure o tipo de informação do item como Character para receber a string, e a conversão será feita nos gatilhos.
📚 Lições Aprendidas (Para a Posteridade)
Zsh no macOS: Nunca cole scripts com ! direto no terminal. Use arquivos .sh.

Isolamento é tudo: Usar uma rede Docker (cpd-net) e um broker local evitou expor o Zabbix à internet, usando uma "ponte" para puxar os dados.

Infraestrutura como Código (IaC): Criar os 7 itens dependentes manualmente levaria 15 minutos e seria sujeito a erros. O script configurar_zabbix.py provou que a API do Zabbix é rápida, idempotente e à prova de erros de digitação.

O tipo External check é o "canivete suíço": Quando o Zabbix luta contra scripts shell (parser interno), empacotar o comando em um .sh no container e chamá-lo via External Check é a solução mais robusta.

Dockerfile customizado: Sobrescrever entrypoint ou command de imagens oficiais é uma armadilha. A melhor prática é estender a imagem com um Dockerfile e instalar as dependências (mosquitto-clients) na construção.

📂 Estrutura de Pastas
text
monitoramento-cpd/
├── .env.example
├── .env                    (não versionado)
├── docker-compose.yml
├── configurar_zabbix.py    (script IaC)
├── docs/
│   └── 00-plano.md
├── mosquitto/
│   └── config/
│       ├── mosquitto.conf
│       └── conf.d/
│           └── bridge.conf
├── zabbix-server-custom/
│   └── Dockerfile          (instala mosquitto-clients)
└── README.md               (este arquivo)
🔮 Próximos Passos (Roadmap)
☑ Fatia 0: Base Docker
☑ Fatia 1: Ponte MQTT
☑ Fatia 2: Ingestão no Zabbix (via IaC)
□ Fatia 3: Gatilhos e Telegram
□ Fatia 4: Dashboard no Grafana
□ Fatia 5: Configuração 100% via código (idempotente)
□ Fatia 6: Painel NOC 3D
□ Fatia 7: Ações (HMAC)
text

---

## O que foi consolidado neste README:

1. **Visão Geral e Arquitetura:** Diagrama de fluxo do Wokwi até o Zabbix.
2. **Passo a Passo (Happy Path):** Como subir o ambiente do zero, sem os erros.
3. **Troubleshooting:** A tabela com **todos os 9 erros** que enfrentamos, com a causa e a solução exata.
4. **Lições Aprendidas:** As 5 grandes lições que valem para qualquer projeto de infraestrutura.
5. **Estrutura de Pastas:** Onde cada arquivo vive.
6. **Roadmap:** O que já foi feito e o que falta.

---

**O que acha?** Se aprovar, podemos:
1. **Salvar este conteúdo no `README.md`** (posso te dar o comando exato).
2. **Partir para a Fatia 3 (Telegram)**, onde vamos criar o Bot e os Gatilhos via Python, adicionando uma nova seção a este documento no final.

Me diga se quer ajustar algo antes de salvar! 🚀








# 🏢 Monitoramento CPD: Físico e Lógico (ESP32 + Zabbix + Grafana + MQTT)

Este projeto implementa uma solução completa de monitoramento para uma sala de servidores (CPD). Ele une o **monitoramento físico** (sensores de temperatura, porta, presença, etc. em um ESP32) com o **monitoramento lógico** (coleta centralizada, processamento e visualização) usando um ecossistema moderno e conteinerizado.

## 📌 Visão Geral da Arquitetura

O fluxo de dados foi desenhado para ser isolado e reprodutível localmente, usando o Wokwi (simulador) como fonte de dados nesta fase.

1. **Dispositivo (ESP32/Wokwi):** Simula os sensores e publica um payload JSON em um broker público (`broker.emqx.io`).
2. **Ponte MQTT (Mosquitto Local):** Um container Mosquitto roda localmente, assina os tópicos do broker público e os republica internamente com o prefixo `publico/`.
3. **Banco de Dados e Orquestração (Zabbix):** O Zabbix Server (via script externo customizado) lê os tópicos do Mosquitto local. Ele extrai os dados individuais (JSONPath) e armazena no PostgreSQL.
4. **Visualização (Grafana):** O Grafana consome os dados via API do Zabbix e exibe em dashboards provisionados via código (JSON).

**Diagrama do Fluxo:**
```text
[ Wokwi (ESP32) ]
      │ (MQTT - Internet)
      ▼
[ broker.emqx.io ]
      │ (Bridge MQTT)
      ▼
[ cpd-mosquitto ] (Docker - cpd-net)
      │ (External Check via script .sh)
      ▼
[ cpd-zabbix-server ] ──> [ cpd-postgres ]
      │ (API)
      ▼
[ cpd-grafana ] (Provisionado via JSON)
🛠️ Pré-requisitos
Sistema Operacional: macOS (testado em Mac mini M4 Apple Silicon) ou Linux.

Docker Desktop instalado e em execução (com suporte a arm64 nativo).

Python 3 (para rodar scripts de automação IaC).

Wokwi (simulador online) configurado para rodar o firmware do ESP32.

🚀 Passo a Passo (Happy Path)
1. Preparar o Ambiente
Clone o repositório e crie o arquivo de variáveis de ambiente:

bash
git clone <url-do-repositorio>
cd monitoramento-cpd
cp .env.example .env
Abra o .env e preencha as senhas do PostgreSQL e do Grafana.

⚠️ Atenção: Se a senha tiver caracteres especiais (#, $, !, espaço), coloque-a entre aspas duplas (ex: POSTGRES_PASSWORD="minha#senha").

2. Subir a Infraestrutura Base
bash
docker compose up -d
docker compose ps
Aguarde até que todos os containers (cpd-mosquitto, cpd-postgres, cpd-zabbix-server, cpd-zabbix-web, cpd-grafana) estejam Up (healthy). O Zabbix Web estará disponível em http://localhost:8080 (Admin/zabbix).

3. Configurar a Ponte MQTT (Mosquitto)
Para que o Zabbix local receba os dados do Wokwi sem expor sua rede, usamos uma bridge no Mosquitto.

O arquivo mosquitto/config/conf.d/bridge.conf já está configurado.

Certifique-se de que a linha include_dir /mosquitto/config/conf.d está ativa no mosquitto.conf.

Teste com o Wokwi rodando:

bash
docker compose exec mosquitto mosquitto_sub -h localhost -t 'publico/#' -v
4. Configurar o Zabbix via Infraestrutura como Código (IaC)
Não crie itens manualmente na interface. Use o script de automação para criar o Host, o Item Mestre e os 9 itens dependentes.

bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests python-dotenv
python configurar_zabbix.py
O script lerá o arquivo .env (adicione ZABBIX_URL, ZABBIX_USER, ZABBIX_PASSWORD nele) e criará toda a árvore de monitoramento de forma idempotente.

5. Configurar o Dashboard no Grafana
O Grafana é provisionado automaticamente via arquivos JSON e YAML. Não é necessário criar painéis manualmente.

O datasource do Zabbix é criado via grafana/provisioning/datasources/zabbix.yaml.

O dashboard é carregado via grafana/dashboards/cpd-dashboard.json.

Importante: O plugin do Zabbix (alexanderzobnin-zabbix-app) precisa ser habilitado manualmente na primeira vez:

Acesse http://localhost:3000 (admin / senha do .env).

Vá em Administration → Plugins, procure "Zabbix" e clique em Enable.

Acesse Dashboards → CPD → CPD Dashboard para ver os dados em tempo real.

6. Verificar os Dados
Acesse http://localhost:8080 (Zabbix). Vá em Monitoring → Latest data, filtre pelo host esp32-cpd e veja os 10 itens (Temperatura, Umidade, Porta, etc.) atualizando em tempo real.

🚑 Troubleshooting (Enciclopédia de Erros)
Esta seção documenta os problemas reais encontrados durante a construção e suas soluções.

Sintoma / Erro	Causa Provável	Solução
zsh: event not found: ) ao colar scripts no terminal do Mac.	O zsh interpreta o caractere ! como histórico.	Salve o comando em um arquivo .sh e execute com bash arquivo.sh, ou use aspas simples.
Mosquitto morre com Unknown configuration variable "include".	O Mosquitto 2.x substituiu include por include_dir.	Coloque os arquivos .conf na pasta conf.d/ e use include_dir /mosquitto/config/conf.d.
Mosquitto morre com Empty bridge remote_username value.	Diretivas de autenticação vazias causam erro fatal.	Remova as linhas remote_username e remote_password do bridge.conf se o broker for anônimo.
Mosquitto morre com Unknown configuration variable "local_prefix".	A sintaxe da ponte foi alterada no Mosquitto 2.x.	O prefixo deve ir na própria linha do tópico: topic topico/remoto in 1 publico/ "".
Zabbix Server entra em loop: ERROR: "LogType" "console" parameter can only be used with the -f.	O command do Docker Compose sobrescreveu o entrypoint do container.	Crie um Dockerfile customizado (zabbix-server-custom). Instale o mosquitto-clients via apk e não sobrescreva o entrypoint original.
Item tipo Script do Zabbix dá SyntaxError: unterminated statement.	O parser interno do Zabbix se confunde com hífens (flags) de comandos shell.	Mude o item para o tipo External check e crie o script físico (mqtt_status.sh) dentro da pasta /usr/lib/zabbix/externalscripts/ do container, com permissão de execução (chmod +x).
Item dependente dá erro: Value of type "string" is not suitable for value type "Numeric (float)".	O passo de Preprocessing (JSONPath) não foi adicionado ou está vazio.	Na aba Preprocessing do item, adicione o passo JSONPath com o caminho exato (ex: $.temp_c).
API do Zabbix retorna unexpected parameter "hostid".	O item.update não aceita hostid (imutável).	Remova o hostid do payload de update. Use-o apenas no create.
API do Zabbix retorna value must be 0 (trends).	trends > 0 só é válido para itens numéricos (float).	Para texto (4) e unsigned (3), use trends: "0". Calcule dinamicamente no script Python.
Painel do Grafana mostra No data.	O filtro do item no JSON ("filter") não bate com o nome exato.	Use "item": { "key": "esp32.temp" } ou o nome exato do item no Zabbix.
Painel "Modo" e "Estado" no Grafana mostram 0 ou No data.	O painel stat não aceita texto (value_type=4).	Mude o tipo do painel para table. O table aceita qualquer tipo de dado.
Plugin do Zabbix não aparece no Grafana.	O plugin vem desabilitado por padrão.	Vá em Administration → Plugins, procure "Zabbix" e clique em Enable.
📚 Lições Aprendidas (Para a Posteridade)
Zsh no macOS: Nunca cole scripts com ! direto no terminal. Use arquivos .sh.

Isolamento é tudo: Usar uma rede Docker (cpd-net) e um broker local evitou expor o Zabbix à internet, usando uma "ponte" para puxar os dados.

Infraestrutura como Código (IaC): Criar os 7 itens dependentes manualmente levaria 15 minutos e seria sujeito a erros. O script configurar_zabbix.py provou que a API do Zabbix é rápida, idempotente e à prova de erros.

O tipo External check é o "canivete suíço": Quando o Zabbix luta contra scripts shell, empacotar o comando em um .sh no container e chamá-lo via External Check é a solução mais robusta.

Dockerfile customizado: Sobrescrever entrypoint ou command de imagens oficiais é uma armadilha. A melhor prática é estender a imagem com um Dockerfile.

Grafana: table para texto: O painel stat só lida com números. Para texto (value_type=4), use table com displayMode: "gradient".

Grafana: allowUiUpdates: false: Com essa configuração, o JSON é a fonte da verdade e a UI é apenas visualização. Para mudar algo, edite o JSON e reinicie o container.

📂 Estrutura de Pastas
text
monitoramento-cpd/
├── .env.example
├── .env                    (não versionado)
├── docker-compose.yml
├── configurar_zabbix.py    (script IaC)
├── docs/
│   └── 00-plano.md
├── mosquitto/
│   └── config/
│       ├── mosquitto.conf
│       └── conf.d/
│           └── bridge.conf
├── zabbix-server-custom/
│   └── Dockerfile          (instala mosquitto-clients)
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/zabbix.yaml
│   │   └── dashboards/default.yaml
│   └── dashboards/
│       └── cpd-dashboard.json
└── README.md               (este arquivo)
🔮 Próximos Passos (Roadmap)
☑ Fatia 0: Base Docker
☑ Fatia 1: Ponte MQTT
☑ Fatia 2: Ingestão no Zabbix (via IaC)
□ Fatia 3: Gatilhos e Telegram (adiada)
☑ Fatia 4: Dashboard no Grafana (via IaC)
☑ Fatia 5: Configuração 100% via código (idempotente)
□ Fatia 6: Painel NOC 3D
□ Fatia 7: Ações (HMAC)
text

---

**O que mudou em relação ao seu README atual:**

1. **Diagrama atualizado:** Agora mostra o Grafana no fluxo.
2. **Passo 5 (Grafana):** Adicionei a seção que faltava, com o passo manual de habilitar o plugin.
3. **Troubleshooting expandido:** De 8 para **12 linhas**, incluindo os erros do Grafana (`stat` vs `table`) e da API do Zabbix (`trends`, `hostid`).
4. **Lições Aprendidas:** De 5 para **7 lições**, incluindo as do Grafana.
5. **Estrutura de Pastas:** Atualizada com as pastas `grafana/provisioning` e `grafana/dashboards`.
6. **Roadmap:** Atualizado com os status reais (Fatias 4 e 5 concluídas).

---

**O que fazer agora:**

1. **Salvar o README:** Cole o conteúdo acima no arquivo `README.md`.
2. **Commitar no Git (se já tiver repo):** `git add . && git commit -m "docs: atualiza README com Fatias 4 e 5"`
3. **Partir para a próxima fatia:** Me diga se quer voltar para o **Telegram (Fatia 3)**, ir para o **NOC 3D (Fatia 6)** ou as **Ações HMAC (Fatia 7)**.

O README está sólido. 🚀
