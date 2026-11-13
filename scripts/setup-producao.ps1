# ============================================================
# setup-producao.ps1 — Automação do IIS + Grafana (Windows 10/11)
# ------------------------------------------------------------
# O que faz:
#   1. Instala o IIS (se não estiver instalado)
#   2. Baixa e instala URL Rewrite + ARR
#   3. Habilita o proxy no ARR
#   4. Configura preserveHostHeader (necessário para Grafana > 8.3.5)
#   5. Cria o web.config com a regra de rewrite
#   6. Ajusta o grafana.ini (adiciona seção [server])
#   7. Reinicia o IIS
# ------------------------------------------------------------
# Uso:
#   1. Abra o PowerShell como Administrador
#   2. Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   3. .\setup-producao.ps1
# ============================================================

$ErrorActionPreference = "Stop"

# ============================================================
# CONFIGURAÇÃO (ALTERE AQUI)
# ============================================================
$Dominio = "monitoramento.suaempresa.com"
$SubPath = "grafana"
$GrafanaPorta = 3000
$GrafanaIniPath = "C:\monitoramento-cpd\grafana\config\grafana.ini"
$IISRoot = "C:\inetpub\wwwroot"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  SETUP DE PRODUÇÃO — monitoramento-cpd" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Domínio: $Dominio"
Write-Host "Sub-path: /$SubPath/"
Write-Host "Porta do Grafana: $GrafanaPorta"
Write-Host ""

# ============================================================
# 1. VERIFICAR SE ESTÁ RODANDO COMO ADMIN
# ============================================================
Write-Host "[1/7] Verificando privilégios..." -ForegroundColor Yellow
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERRO: Execute como Administrador." -ForegroundColor Red
    exit 1
}
Write-Host "  OK: Rodando como Administrador." -ForegroundColor Green

# ============================================================
# 2. INSTALAR IIS
# ============================================================
Write-Host "[2/7] Verificando IIS..." -ForegroundColor Yellow
if (-not (Get-WindowsFeature -Name Web-Server).Installed) {
    Write-Host "  Instalando IIS..."
    Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServerRole -All -NoRestart
    Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServer -All -NoRestart
    Enable-WindowsOptionalFeature -Online -FeatureName IIS-CommonHttpFeatures -All -NoRestart
    Enable-WindowsOptionalFeature -Online -FeatureName IIS-HttpRedirect -All -NoRestart
    Enable-WindowsOptionalFeature -Online -FeatureName IIS-ApplicationDevelopment -All -NoRestart
    Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebSockets -All -NoRestart
    Enable-WindowsOptionalFeature -Online -FeatureName IIS-ManagementConsole -All -NoRestart
    Write-Host "  OK: IIS instalado." -ForegroundColor Green
} else {
    Write-Host "  OK: IIS já instalado." -ForegroundColor Green
}

# ============================================================
# 3. INSTALAR URL REWRITE + ARR
# ============================================================
Write-Host "[3/7] Verificando URL Rewrite e ARR..." -ForegroundColor Yellow

# Verifica se o URL Rewrite está instalado
$urlRewritePath = "$env:windir\system32\inetsrv\rewrite.dll"
$urlRewriteInstalled = Test-Path $urlRewritePath

# Verifica se o ARR está instalado
$arrPath = "$env:ProgramFiles\IIS\Application Request Routing"
$arrInstalled = Test-Path $arrPath

if (-not $urlRewriteInstalled -or -not $arrInstalled) {
    Write-Host "  Baixando instaladores (URL Rewrite + ARR)..." -ForegroundColor Yellow

    # URL Rewrite
    if (-not $urlRewriteInstalled) {
        $urlRewriteUrl = "https://download.microsoft.com/download/1/2/8/128E2E22-C1B9-44A4-BE2A-5859ED1D4592/rewrite_amd64_en-US.msi"
        $urlRewriteMsi = "$env:TEMP\rewrite_amd64.msi"
        Write-Host "    Baixando URL Rewrite..."
        Invoke-WebRequest -Uri $urlRewriteUrl -OutFile $urlRewriteMsi -UseBasicParsing
        Write-Host "    Instalando URL Rewrite..."
        Start-Process msiexec.exe -ArgumentList "/i `"$urlRewriteMsi`" /qn /norestart" -Wait
        Write-Host "    OK: URL Rewrite instalado." -ForegroundColor Green
    } else {
        Write-Host "  OK: URL Rewrite já instalado." -ForegroundColor Green
    }

    # ARR
    if (-not $arrInstalled) {
        $arrUrl = "https://download.microsoft.com/download/E/9/8/E9849D6A-020E-47E4-9FD0-A023E99B54EB/requestRouter_amd64.msi"
        $arrMsi = "$env:TEMP\requestRouter_amd64.msi"
        Write-Host "    Baixando ARR..."
        Invoke-WebRequest -Uri $arrUrl -OutFile $arrMsi -UseBasicParsing
        Write-Host "    Instalando ARR..."
        Start-Process msiexec.exe -ArgumentList "/i `"$arrMsi`" /qn /norestart" -Wait
        Write-Host "    OK: ARR instalado." -ForegroundColor Green
    } else {
        Write-Host "  OK: ARR já instalado." -ForegroundColor Green
    }
} else {
    Write-Host "  OK: URL Rewrite e ARR já instalados." -ForegroundColor Green
}

# ============================================================
# 4. HABILITAR PROXY NO ARR + preserveHostHeader
# ============================================================
Write-Host "[4/7] Configurando ARR..." -ForegroundColor Yellow
Import-Module WebAdministration
Set-WebConfigurationProperty -PSPath 'MACHINE/WEBROOT/APPHOST' -Filter "system.webServer/proxy" -Name "enabled" -Value "True"
& $env:windir\system32\inetsrv\appcmd.exe set config -section:system.webServer/proxy -preserveHostHeader:true /commit:apphost
Write-Host "  OK: Proxy do ARR habilitado." -ForegroundColor Green

# ============================================================
# 5. CRIAR WEB.CONFIG
# ============================================================
Write-Host "[5/7] Criando web.config..." -ForegroundColor Yellow
$webConfigPath = Join-Path $IISRoot "web.config"

# Backup do web.config existente
if (Test-Path $webConfigPath) {
    $backupPath = "$webConfigPath.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item $webConfigPath $backupPath
    Write-Host "  Backup do web.config existente: $backupPath"
}

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

$webConfig | Out-File -FilePath $webConfigPath -Encoding UTF8
Write-Host "  OK: web.config criado em $webConfigPath" -ForegroundColor Green

# ============================================================
# 6. AJUSTAR GRAFANA.INI
# ============================================================
Write-Host "[6/7] Ajustando grafana.ini..." -ForegroundColor Yellow

if (Test-Path $GrafanaIniPath) {
    $ini = Get-Content $GrafanaIniPath -Raw

    if ($ini -match '\[server\]') {
        Write-Host "  AVISO: Seção [server] já existe. Verifique manualmente." -ForegroundColor Yellow
    } else {
        $serverSection = @"

[server]
domain = $Dominio
root_url = https://$Dominio/$SubPath/
serve_from_sub_path = true
"@
        $ini = $serverSection + $ini
        $ini | Out-File -FilePath $GrafanaIniPath -Encoding UTF8 -NoNewline
        Write-Host "  OK: Seção [server] adicionada ao grafana.ini." -ForegroundColor Green
    }
} else {
    Write-Host "  ERRO: grafana.ini não encontrado em $GrafanaIniPath" -ForegroundColor Red
    Write-Host "  Crie manualmente ou ajuste o caminho no script." -ForegroundColor Red
}

# ============================================================
# 7. REINICIAR IIS
# ============================================================
Write-Host "[7/7] Reiniciando IIS..." -ForegroundColor Yellow
Restart-Service W3SVC -Force
Write-Host "  OK: IIS reiniciado." -ForegroundColor Green

# ============================================================
# RESUMO
# ============================================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  ✅ AUTOMAÇÃO CONCLUÍDA" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Próximos passos MANUAIS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. Configure o certificado SSL no IIS:"
Write-Host "     - IIS Manager → Default Web Site → Bindings → Add → https → 443"
Write-Host "     - Selecione o certificado (Let's Encrypt ou self-signed)"
Write-Host ""
Write-Host "  2. Suba o Docker Desktop e rode:"
Write-Host "     cd C:\monitoramento-cpd"
Write-Host "     docker compose up -d"
Write-Host ""
Write-Host "  3. Teste o Grafana:"
Write-Host "     https://$Dominio/$SubPath/"
Write-Host ""
Write-Host "  4. Teste o NOC 3D:"
Write-Host "     https://$Dominio/$SubPath/public/grafana-custom/noc/noc3d.html"
Write-Host ""
Write-Host "Se der ERR_TOO_MANY_REDIRECTS:" -ForegroundColor Yellow
Write-Host "  - Edite $webConfigPath"
Write-Host "  - Troque {R:2} por {R:0} na ação do rewrite"
Write-Host ""
