
---

## 🎯 O que está no README

| Seção | O que cobre |
|---|---|
| **O que você vai precisar** | Tabela de pré-requisitos com links de download |
| **Fase 1** | WSL2, Docker Desktop, Git, Make, Python 3 |
| **Fase 2** | Clonar o projeto, criar `.env`, venv, rodar testes |
| **Fase 3** | Subir a stack, rodar IaC, testar NOC 3D |
| **Fase 4** | Instalar IIS, URL Rewrite, ARR, `web.config` |
| **Fase 5** | Configurar o `grafana.ini` com sub-path |
| **Fase 6** | Configurar HTTPS (Let's Encrypt ou self-signed) |
| **Checklist** | 12 itens para verificar antes de considerar "pronto" |
| **Troubleshooting** | 7 problemas comuns com causa e solução |
| **Referências** | Links oficiais |

---

## 🎯 Como usar amanhã

1. **Antes de ligar o Windows**, leia o README no Mac para se familiarizar com as fases.
2. **No Windows**, siga a ordem: **Fase 1 → Fase 2 → Fase 3 → Fase 4 → Fase 5 → Fase 6**.
3. **Cada fase tem um "Teste"** — só avance se o teste passar.
4. **Se algo der errado**, consulte o **Troubleshooting** (seção final).

---

## 🎯 Bônus: script PowerShell para automatizar a Fase 4

Se quiser automatizar a instalação do IIS + URL Rewrite + ARR + `web.config`, salve o script abaixo como `C:\monitoramento-cpd\scripts\setup-producao.ps1` e rode como **Administrador**:

```powershell
# setup-producao.ps1
# Roda como Administrador no Windows.

$ErrorActionPreference = "Stop"
$Dominio = "monitoramento.suaempresa.com"   # ALTERE AQUI
$SubPath = "grafana"
$GrafanaPorta = 3000

Write-Host "=== 1. Instalando IIS ===" -ForegroundColor Cyan
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServerRole -All
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServer -All
Enable-WindowsOptionalFeature -Online -FeatureName IIS-CommonHttpFeatures -All

Write-Host "=== 2. Habilitando proxy no ARR ===" -ForegroundColor Cyan
# (assume que URL Rewrite + ARR já estão instalados manualmente)
Set-WebConfigurationProperty -PSPath 'MACHINE/WEBROOT/APPHOST' -Filter "system.webServer/proxy" -Name "enabled" -Value "True"
& $env:windir\system32\inetsrv\appcmd.exe set config -section:system.webServer/proxy -preserveHostHeader:true /commit:apphost

Write-Host "=== 3. Criando web.config ===" -ForegroundColor Cyan
$webConfig = @"
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="Grafana Inbound Rule" enabled="true" stopProcessing="true">
          <match url="$SubPath(/)?(.*)" />
          <action type="Rewrite" url="http://localhost:$GrafanaPorta/{R:2}" logRewrittenUrl="false" />
        </rule>
      </rules>
    </rewrite>
  </system.webServer>
</configuration>
"@
$webConfig | Out-File -FilePath "C:\inetpub\wwwroot\web.config" -Encoding UTF8

Write-Host "=== 4. Ajustando grafana.ini ===" -ForegroundColor Cyan
$iniPath = "C:\monitoramento-cpd\grafana\config\grafana.ini"
$ini = Get-Content $iniPath -Raw
if ($ini -notmatch '\[server\]') {
    $serverSection = @"

[server]
domain = $Dominio
root_url = https://$Dominio/$SubPath/
serve_from_sub_path = true
"@
    $ini = $serverSection + $ini
    $ini | Out-File -FilePath $iniPath -Encoding UTF8 -NoNewline
}

Write-Host "=== 5. Reiniciando IIS ===" -ForegroundColor Cyan
Restart-Service W3SVC -Force

Write-Host ""
Write-Host "✅ Automação concluída!" -ForegroundColor Green
Write-Host "Próximos passos:"
Write-Host "  1. Configure o certificado SSL no IIS (Binding HTTPS)."
Write-Host "  2. Rode: docker compose up -d"
Write-Host "  3. Teste: https://$Dominio/$SubPath/"# (cole aqui o conteúdo do README que eu te passei)























# 🪟 Configuração de Produção no Windows 10/11

Guia completo para migrar o projeto `monitoramento-cpd` do Mac (desenvolvimento)
para Windows 10/11 (produção).

**Versão do guia:** 1.1
**Data:** 2026-11-12
**Autor:** Cristiano

---

## 🏛️ Decisões de arquitetura relacionadas

Antes de seguir, leia os ADRs que registram as decisões deste guia:

- [ADR-007](adr/007-windows-10-producao.md) — Windows 10 como ambiente de produção (legado).
- [ADR-008](adr/008-windows-11-producao.md) — Windows 11 como ambiente de produção (futuro).
- [ADR-004](adr/004-3d-via-iframe.md) — NOC 3D via iframe (por que não plugin nativo).
- [ADR-005](adr/005-grafana-via-json.md) — Grafana via JSON (por que não cliques).

---

## 🤖 Script de automação (Fase 4)

A **Fase 4 (IIS)** tem um script que automatiza quase tudo:

- **Local:** `scripts/setup-producao.ps1`
- **O que faz:**
  1. Instala o IIS (se não estiver instalado).
  2. Baixa e instala **URL Rewrite** + **ARR**.
  3. Habilita o proxy no ARR.
  4. Configura `preserveHostHeader` (necessário para Grafana > 8.3.5).
  5. Cria o `web.config` (com backup do existente).
  6. Ajusta o `grafana.ini` (adiciona a seção `[server]`).
  7. Reinicia o IIS.
- **O que NÃO faz (manual):** certificado SSL, subir o Docker, testar o NOC 3D.

### Como usar o script

```powershell
# No Windows, como Administrador:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
cd C:\monitoramento-cpd
.\scripts\setup-producao.ps1
Antes de rodar, ajuste as variáveis no topo do script:

powershell
$Dominio = "monitoramento.suaempresa.com"   # seu domínio real
$GrafanaIniPath = "C:\monitoramento-cpd\grafana\config\grafana.ini"
Depois do script
Configure o certificado SSL no IIS (Binding HTTPS na porta 443).

Suba o Docker Desktop e rode docker compose up -d.

Teste: https://monitoramento.suaempresa.com/grafana/.

Teste o NOC 3D: https://monitoramento.suaempresa.com/grafana/public/grafana-custom/noc/noc3d.html.

📋 O que você vai precisar
Item	O que é	Onde baixar
Windows 10/11	Sistema operacional	Já tem
Docker Desktop	Roda a stack (Mosquitto, Zabbix, Grafana, Postgres)	https://www.docker.com/products/docker-desktop/
WSL2	Necessário para o Docker Desktop no Windows	wsl --install (PowerShell Admin)
Git	Clonar o repositório	https://git-scm.com/download/win
Make	Rodar o Makefile	choco install make ou http://gnuwin32.sourceforge.net/packages/make.htm
Python 3	Rodar os scripts de IaC	https://www.python.org/downloads/windows/
IIS	Servidor web para o proxy reverso	Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServerRole (PowerShell Admin)
URL Rewrite	Módulo do IIS	https://www.iis.net/downloads/microsoft/url-rewrite
ARR	Módulo do IIS	https://www.iis.net/downloads/microsoft/application-request-routing
Certificado SSL	HTTPS em produção	Let's Encrypt (win-acme) ou CA interna
Ordem de instalação obrigatória:

WSL2 → Docker Desktop

Git → clone do projeto

Python 3 → venv + dependências

IIS → URL Rewrite → ARR

Certificado SSL

🎯 Fase 1 — Preparar o Windows
1.1 Instalar WSL2 + Docker Desktop
powershell
# PowerShell como Administrador
wsl --install
Reinicie o Windows. Depois, instale o Docker Desktop (o instalador detecta o WSL2 e configura tudo).

Teste:

powershell
docker --version
docker compose version
O que esperar:

text
Docker version 27.x.x, build xxxxx
Docker Compose version v2.x.x
1.2 Instalar Git
powershell
winget install --id Git.Git -e
Teste:

powershell
git --version
O que esperar: git version 2.x.x.windows.x

1.3 Instalar Make
powershell
winget install --id GnuWin32.Make -e
Ou, se preferir Chocolatey:

powershell
choco install make -y
Teste:

powershell
make --version
O que esperar: GNU Make 3.81 (ou superior).

1.4 Instalar Python 3
powershell
winget install --id Python.Python.3.11 -e
Teste:

powershell
python --version
O que esperar: Python 3.11.x

🎯 Fase 2 — Clonar o projeto
2.1 Clonar o repositório
powershell
cd C:\
git clone https://github.com/CrisisUp/monitoramento-cpd.git
cd monitoramento-cpd
Teste:

powershell
ls
O que esperar:

text
Makefile
docker-compose.yml
configurar_zabbix.py
grafana/
firmware/
tests/
docs/
...
2.2 Criar o .env
powershell
cp .env.example .env
notepad .env
O que preencher:

Variável	Valor
POSTGRES_PASSWORD	senha forte (ex: PostgresForte2026!)
GRAFANA_ADMIN_PASSWORD	senha forte (ex: GrafanaForte2026!)
⚠️ Atenção: se a senha tiver #, $, !, espaço ou ", coloque entre aspas duplas no .env:

text
POSTGRES_PASSWORD="minha#senha"
2.3 Criar o venv Python
powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --quiet requests python-dotenv pytest pytest-mock jsonschema
Teste:

powershell
pytest
O que esperar: 20 passed in 0.5s (os 20 testes do projeto).

🎯 Fase 3 — Subir a stack
3.1 Subir o Docker
powershell
docker compose up -d
Aguarde ~30s (primeira vez baixa as imagens, ~1.5 GB).

Teste:

powershell
docker compose ps
O que esperar:

text
cpd-mosquitto       Up (healthy)
cpd-postgres        Up (healthy)
cpd-zabbix-server   Up
cpd-zabbix-web      Up (healthy)
cpd-grafana         Up
3.2 Configurar o Zabbix via IaC
powershell
.\.venv\Scripts\Activate.ps1
python configurar_zabbix.py
O que esperar:

text
[1/6] Autenticando...
  [+] Login OK
[2/6] Grupo 'CPD'...
  [+] Grupo 'CPD' criado (ID 2)
...
✅ CONFIGURAÇÃO COMPLETA
3.3 Testar o NOC 3D
powershell
start http://localhost:3000/public/grafana-custom/noc/noc3d.html
O que esperar: a sala 3D com o rack, porta, sensor, ar-condicionado.

🎯 Fase 4 — Configurar o IIS (proxy reverso)
Recomendado: use o script scripts/setup-producao.ps1 (automatiza 80% desta fase). Se preferir manual, siga os passos abaixo.

4.1 Instalar IIS
powershell
# PowerShell como Administrador
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServerRole -All
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServer -All
Enable-WindowsOptionalFeature -Online -FeatureName IIS-CommonHttpFeatures -All
Enable-WindowsOptionalFeature -Online -FeatureName IIS-HttpRedirect -All
Enable-WindowsOptionalFeature -Online -FeatureName IIS-ApplicationDevelopment -All
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebSockets -All
Enable-WindowsOptionalFeature -Online -FeatureName IIS-ManagementConsole -All
Teste:

powershell
start http://localhost
O que esperar: a página padrão do IIS ("Welcome to IIS").

4.2 Instalar URL Rewrite + ARR
Ordem importa: URL Rewrite antes do ARR.

URL Rewrite:

Baixe em https://www.iis.net/downloads/microsoft/url-rewrite.

Instale (.msi).

Reinicie o IIS (iisreset).

ARR:

Baixe em https://www.iis.net/downloads/microsoft/application-request-routing.

Instale (.msi).

Reinicie o IIS (iisreset).

Teste:

Abra o IIS Manager → clique no servidor (não no site) → veja se aparecem os ícones:

URL Rewrite (na seção "IIS")

Application Request Routing Cache (na seção "IIS")

4.3 Habilitar o proxy no ARR
No IIS Manager, clique no servidor (não no site).

Duplo clique em Application Request Routing Cache.

No painel direito, clique em Server Proxy Settings.

Marque Enable proxy.

Apply.

⚠️ Sem isso, o IIS retorna 404 mesmo com o web.config correto.

4.4 Configurar o preserveHostHeader
powershell
# PowerShell como Administrador
& $env:windir\system32\inetsrv\appcmd.exe set config -section:system.webServer/proxy -preserveHostHeader:true /commit:apphost
Por quê: necessário para o Grafana > 8.3.5 funcionar atrás do IIS.

4.5 Criar o web.config
Salve o arquivo em C:\inetpub\wwwroot\web.config:

xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
  <system.webServer>
    <rewrite>
      <rules>
        <rule name="Grafana Inbound Rule" enabled="true" stopProcessing="true">
          <match url="grafana(/)?(.*)" />
          <action type="Rewrite" url="http://localhost:3000/{R:2}" logRewrittenUrl="false" />
        </rule>
      </rules>
    </rewrite>
  </system.webServer>
</configuration>
⚠️ Se der ERR_TOO_MANY_REDIRECTS: troque {R:2} por {R:0}:

xml
<action type="Rewrite" url="http://localhost:3000{R:0}" />
4.6 Testar o IIS
powershell
start http://localhost/grafana/
O que esperar: a página de login do Grafana.

Se der 404:

Verifique se o proxy do ARR está habilitado (passo 4.3).

Verifique se o web.config está em C:\inetpub\wwwroot\.

🎯 Fase 5 — Configurar o Grafana com sub-path
5.1 Editar o grafana.ini
powershell
notepad C:\monitoramento-cpd\grafana\config\grafana.ini
Adicione a seção [server] antes de [security]:

ini
[server]
domain = monitoramento.suaempresa.com
root_url = http://localhost/grafana/
serve_from_sub_path = true

[security]
disable_sanitize_html = true
allow_embedding = true
cookie_samesite = disabled

[panels]
disable_sanitize_html = true

[analytics]
reporting_enabled = false
⚠️ Atenção ao root_url:

Se estiver testando sem HTTPS, use http://localhost/grafana/.

Se estiver em produção com domínio, use https://monitoramento.suaempresa.com/grafana/.

Sempre com /grafana/ no final (a barra é obrigatória).

5.2 Recriar o Grafana
powershell
cd C:\monitoramento-cpd
docker compose up -d --force-recreate grafana
Teste:

powershell
start http://localhost/grafana/
O que esperar: o login do Grafana, com os links internos funcionando.

5.3 Testar o NOC 3D via IIS
powershell
start http://localhost/grafana/public/grafana-custom/noc/noc3d.html
O que esperar: a sala 3D, com o badge mostrando dados reais do Zabbix.

Se não aparecer:

Verifique se o noc3d.html está usando o proxy do datasource (/api/datasources/proxy/uid/zabbix/...).

Verifique o Console (F12) para erros de CORS ou 404.

🎯 Fase 6 — Configurar o HTTPS (produção)
6.1 Gerar certificado SSL
Opção A — Let's Encrypt (recomendado para domínio público):

powershell
# Instalar win-acme
winget install --id WACS.WACS -e

# Gerar certificado
wacs.exe --target iis --host monitoramento.suaempresa.com
Opção B — Certificado self-signed (para testes internos):

powershell
New-SelfSignedCertificate -DnsName "monitoramento.suaempresa.com" -CertStoreLocation "Cert:\LocalMachine\My"
6.2 Configurar o binding HTTPS no IIS
No IIS Manager, clique no site (Default Web Site).

No painel direito, clique em Bindings.

Add → Type: https → Port: 443 → SSL certificate: selecione o certificado.

OK.

6.3 Ajustar o root_url para HTTPS
powershell
notepad C:\monitoramento-cpd\grafana\config\grafana.ini
Mude:

ini
root_url = https://monitoramento.suaempresa.com/grafana/
E recrie:

powershell
docker compose up -d --force-recreate grafana
6.4 Testar o HTTPS
powershell
start https://monitoramento.suaempresa.com/grafana/
O que esperar: o login do Grafana com cadeado verde.

✅ Checklist final
Antes de considerar "produção pronta", verifique:

□ Docker Desktop rodando
□ docker compose ps mostra 5 containers Up
□ http://localhost:3000/grafana/ abre o login
□ http://localhost:3000/grafana/public/grafana-custom/noc/noc3d.html mostra o 3D
□ http://localhost/grafana/ abre o login (via IIS)
□ http://localhost/grafana/public/grafana-custom/noc/noc3d.html mostra o 3D (via IIS)
□ HTTPS configurado (se aplicável)
□ https://monitoramento.suaempresa.com/grafana/ abre o login
□ pytest passa 20 testes
□ make test funciona
□ Backup configurado (make backup cria arquivo em backups/)
□ .env não está no Git (git check-ignore .env)
🚑 Troubleshooting
IIS retorna 404 em /grafana/
Causa: o proxy do ARR não está habilitado.
Solução: IIS Manager → servidor → Application Request Routing Cache → Server Proxy Settings → Enable proxy → Apply.

ERR_TOO_MANY_REDIRECTS
Causa: conflito entre root_url e a regra de rewrite.
Solução: troque {R:2} por {R:0} no web.config.

Grafana mostra "Site can't be reached"
Causa: o IIS não está conseguindo falar com o Grafana.
Solução: verifique se o Grafana está Up (docker compose ps) e se o web.config aponta para http://localhost:3000.

NOC 3D mostra "No data" ou erro de CORS
Causa: o proxy do datasource do Grafana não está configurado.
Solução: verifique se o grafana/provisioning/datasources/zabbix.yaml tem uid: zabbix e se o noc3d.html usa /api/datasources/proxy/uid/zabbix/api_jsonrpc.php.

Certificado SSL não aparece nos bindings do IIS
Causa: o certificado não está no store LocalMachine\My.
Solução: importe o .pfx via Import-PfxCertificate ou use o win-acme para gerar.

Docker Desktop não inicia no Windows
Causa: WSL2 não está configurado.
Solução: wsl --install (PowerShell Admin), reinicie, abra o Docker Desktop.

📚 Referências
Grafana + IIS: guia oficial

URL Rewrite + ARR (Microsoft)

win-acme (Let's Encrypt para Windows)

Docker Desktop no Windows

🎯 Próximos passos
Depois que tudo estiver funcionando:

Configure o alerta no Telegram (Fatia 3 — adiada).

Configure o backup automático (agendador de tarefas do Windows rodando make backup diariamente).

Configure o monitoramento do próprio pipeline (Prometheus + Grafana) — item 9 da lista de melhorias.

Documente a escalabilidade (adicionar uma segunda sala/CPD) — item 10 da lista de melhorias.
