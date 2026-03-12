#Requires -Version 5.1
# =============================================================================
# install.ps1 — ISBN Renamer: instalação para Windows
# Execute com: powershell -ExecutionPolicy Bypass -File install.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

function Ok    { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Aviso { param($msg) Write-Host "  [!]  $msg" -ForegroundColor Yellow }
function Erro  { param($msg) Write-Host "  [X]  $msg" -ForegroundColor Red; exit 1 }
function Info  { param($msg) Write-Host "       $msg" }

Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       ISBN Renamer - Instalacao          ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ─── Verificar winget ─────────────────────────────────────────────────────────
Write-Host "▶ Verificando winget..." -ForegroundColor Cyan
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Erro "winget nao encontrado. Atualize o Windows ou instale o App Installer pela Microsoft Store."
}
Ok "winget disponivel: $(winget --version)"
Write-Host ""

# ─── Função helper: instalar via winget ──────────────────────────────────────
function Instalar-Winget {
    param(
        [string]$Nome,
        [string]$Id,
        [string]$Comando
    )
    Write-Host "  Instalando $Nome..." -NoNewline
    if (Get-Command $Comando -ErrorAction SilentlyContinue) {
        Write-Host " ja instalado." -ForegroundColor Green
        return
    }
    try {
        winget install --id $Id --silent --accept-package-agreements --accept-source-agreements | Out-Null
        Write-Host " OK" -ForegroundColor Green
    } catch {
        Write-Host " FALHOU" -ForegroundColor Red
        Aviso "Instale $Nome manualmente e adicione ao PATH."
    }
}

# ─── Dependências do sistema ──────────────────────────────────────────────────
Write-Host "▶ Instalando dependencias do sistema..." -ForegroundColor Cyan

# Tesseract OCR
Instalar-Winget -Nome "Tesseract OCR" -Id "UB-Mannheim.TesseractOCR" -Comando "tesseract"

# ExifTool
Instalar-Winget -Nome "ExifTool" -Id "OliverBetz.ExifTool" -Comando "exiftool"

# Poppler (winget não tem pacote oficial; fazer download manual)
Write-Host "  Verificando Poppler..." -NoNewline
$popplerOk = $false

# Verificar PATH
if (Get-Command pdftoppm -ErrorAction SilentlyContinue) {
    Write-Host " ja no PATH." -ForegroundColor Green
    $popplerOk = $true
}

# Verificar caminhos padroes
if (-not $popplerOk) {
    $candidatos = @(
        "C:\Program Files\poppler\Library\bin",
        "C:\poppler\Library\bin",
        "C:\poppler\bin"
    )
    # Buscar pasta poppler-* em Program Files
    @("C:\Program Files", "C:\") | ForEach-Object {
        if (Test-Path $_) {
            Get-ChildItem -Path $_ -Directory -Filter "poppler*" -ErrorAction SilentlyContinue | ForEach-Object {
                $candidatos += "$($_.FullName)\Library\bin"
                $candidatos += "$($_.FullName)\bin"
            }
        }
    }
    foreach ($c in $candidatos) {
        if (Test-Path (Join-Path $c "pdftoppm.exe")) {
            Write-Host " encontrado em $c" -ForegroundColor Green
            $popplerOk = $true
            break
        }
    }
}

if (-not $popplerOk) {
    Write-Host ""
    Aviso "Poppler nao encontrado. Instalando via download..."

    $popplerUrl  = "https://github.com/oschwartz10612/poppler-windows/releases/latest/download/Release-24.08.0-0.zip"
    $popplerZip  = "$env:TEMP\poppler.zip"
    $popplerDest = "C:\Program Files\poppler"

    try {
        Write-Host "       Baixando Poppler..."
        Invoke-WebRequest -Uri $popplerUrl -OutFile $popplerZip -UseBasicParsing
        Write-Host "       Extraindo para $popplerDest..."
        Expand-Archive -Path $popplerZip -DestinationPath $popplerDest -Force
        Remove-Item $popplerZip

        # Encontrar a subpasta com pdftoppm.exe
        $popplerBin = Get-ChildItem -Path $popplerDest -Recurse -Filter "pdftoppm.exe" |
                      Select-Object -First 1 | ForEach-Object { $_.DirectoryName }

        if ($popplerBin) {
            # Adicionar ao PATH do sistema permanentemente
            $pathAtual = [Environment]::GetEnvironmentVariable("Path", "Machine")
            if ($pathAtual -notlike "*$popplerBin*") {
                [Environment]::SetEnvironmentVariable("Path", "$pathAtual;$popplerBin", "Machine")
                Info "Poppler adicionado ao PATH do sistema: $popplerBin"
                Info "Reinicie o terminal para que o PATH seja atualizado."
            }
            Ok "Poppler instalado: $popplerBin"
        } else {
            Aviso "Nao foi possivel localizar pdftoppm.exe no zip extraido."
        }
    } catch {
        Aviso "Download automatico falhou: $_"
        Aviso "Baixe manualmente em: https://github.com/oschwartz10612/poppler-windows/releases"
        Aviso "Extraia e adicione a pasta 'bin' ou 'Library\bin' ao PATH."
    }
}

Write-Host ""

# ─── Verificar ferramentas ────────────────────────────────────────────────────
Write-Host "▶ Verificando ferramentas no PATH..." -ForegroundColor Cyan
foreach ($cmd in @("tesseract", "exiftool", "pdftoppm")) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($found) {
        Ok "${cmd} → $($found.Source)"
    } else {
        Aviso "${cmd} nao encontrado no PATH. Pode ser necessario reiniciar o terminal."
    }
}
Write-Host ""

# ─── Instalar uv ──────────────────────────────────────────────────────────────
Write-Host "▶ Verificando uv..." -ForegroundColor Cyan
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Ok "uv ja instalado: $(uv --version)"
} else {
    Write-Host "  Instalando uv..."
    try {
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
        # Recarregar PATH
        $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                    [Environment]::GetEnvironmentVariable("Path","User")
        if (Get-Command uv -ErrorAction SilentlyContinue) {
            Ok "uv instalado: $(uv --version)"
        } else {
            Aviso "uv instalado, mas nao encontrado no PATH atual."
            Aviso "Feche e reabra o terminal, depois execute: uv sync"
        }
    } catch {
        Erro "Falha ao instalar uv: $_"
    }
}
Write-Host ""

# ─── Instalar pacotes Python ──────────────────────────────────────────────────
Write-Host "▶ Instalando pacotes Python com uv..." -ForegroundColor Cyan
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv sync
    Ok "Ambiente Python configurado."
} else {
    Aviso "uv nao disponivel nesta sessao. Execute 'uv sync' apos reiniciar o terminal."
}
Write-Host ""

# ─── Menu de Contexto ─────────────────────────────────────────────────────────
Write-Host "▶ Registrando menu de contexto (clique-direito)..." -ForegroundColor Cyan
$InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$regScript = Join-Path $InstallDir "context_menu\register_windows.ps1"
if (Test-Path $regScript) {
    try {
        & powershell -ExecutionPolicy Bypass -File $regScript -InstallDir $InstallDir
    } catch {
        Aviso "Nao foi possivel registrar o menu de contexto: $_"
        Aviso "Execute manualmente: powershell -ExecutionPolicy Bypass -File context_menu\register_windows.ps1"
    }
} else {
    Aviso "Script de registro nao encontrado: $regScript"
}
Write-Host ""

# ─── Conclusão ────────────────────────────────────────────────────────────────
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        Instalacao concluida!  OK         ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Execute normalmente:  uv run isbn.py" -ForegroundColor White
Write-Host "  Via clique-direito:   botao direito em qualquer pasta no Explorer" -ForegroundColor Yellow
Write-Host ""
Write-Host "  IMPORTANTE: Se alguma ferramenta nao foi encontrada," -ForegroundColor Gray
Write-Host "  reinicie o terminal e verifique o PATH." -ForegroundColor Gray
Write-Host ""
