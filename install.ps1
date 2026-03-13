#Requires -Version 5.1
# =============================================================================
# install.ps1 — ISBN Renamer: instalação para Windows
# Execute com: powershell -ExecutionPolicy Bypass -File install.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

function Ok { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Aviso { param($msg) Write-Host "  [!]  $msg" -ForegroundColor Yellow }
function Erro { param($msg) Write-Host "  [X]  $msg" -ForegroundColor Red; exit 1 }
function Info { param($msg) Write-Host "       $msg" }

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "       ISBN Renamer - Instalacao          " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ─── Verificar winget ─────────────────────────────────────────────────────────
Write-Host "-- Verificando winget..." -ForegroundColor Cyan
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
    }
    catch {
        Write-Host " FALHOU" -ForegroundColor Red
        Aviso "Instale $Nome manualmente e adicione ao PATH."
    }
}

# ─── Dependências do sistema ──────────────────────────────────────────────────
Write-Host "-- Instalando dependencias do sistema..." -ForegroundColor Cyan

# Tesseract OCR
Instalar-Winget -Nome "Tesseract OCR" -Id "UB-Mannheim.TesseractOCR" -Comando "tesseract"

# ExifTool
Instalar-Winget -Nome "ExifTool" -Id "OliverBetz.ExifTool" -Comando "exiftool"

# Poppler
Write-Host "  Verificando Poppler..." -NoNewline
$popplerOk = $false

if (Get-Command pdftoppm -ErrorAction SilentlyContinue) {
    Write-Host " ja no PATH." -ForegroundColor Green
    $popplerOk = $true
}

if (-not $popplerOk) {
    $candidatos = @(
        "$env:USERPROFILE\AppData\Local\poppler\Library\bin",
        "C:\Program Files\poppler\Library\bin",
        "C:\poppler\bin"
    )
    # Busca adicional
    @("C:\Program Files", "$env:USERPROFILE\AppData\Local") | ForEach-Object {
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
    Aviso "Poppler nao encontrado. Instalando..."

    $popplerUrl = "https://github.com/oschwartz10612/poppler-windows/releases/latest/download/Release-24.08.0-0.zip"
    $popplerZip = "$env:TEMP\poppler.zip"
    $popplerDest = "$env:USERPROFILE\AppData\Local\poppler"

    try {
        if (-not (Test-Path $popplerDest)) { New-Item -ItemType Directory -Path $popplerDest -Force | Out-Null }
        Write-Host "       Baixando Poppler..."
        Invoke-WebRequest -Uri $popplerUrl -OutFile $popplerZip -UseBasicParsing
        Write-Host "       Extraindo para $popplerDest..."
        Expand-Archive -Path $popplerZip -DestinationPath $popplerDest -Force
        Remove-Item $popplerZip

        $popplerBin = Get-ChildItem -Path $popplerDest -Recurse -Filter "pdftoppm.exe" |
                      Select-Object -First 1 | ForEach-Object { $_.DirectoryName }

        if ($popplerBin) {
            $pathAtual = [Environment]::GetEnvironmentVariable("Path", "User")
            if ($pathAtual -notlike "*$popplerBin*") {
                [Environment]::SetEnvironmentVariable("Path", "$pathAtual;$popplerBin", "User")
                Info "Poppler adicionado ao PATH do usuario."
            }
            Ok "Poppler instalado: $popplerBin"
            $env:Path += ";$popplerBin"
        }
    }
    catch {
        Aviso "Falha na instalacao automatica do Poppler: $_"
    }
}

Write-Host ""

# ─── Verificar ferramentas ────────────────────────────────────────────────────
Write-Host "-- Verificando ferramentas no PATH..." -ForegroundColor Cyan
foreach ($cmd in @("tesseract", "exiftool", "pdftoppm")) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($found) {
        Ok "${cmd} -> $($found.Source)"
    }
    else {
        Aviso "${cmd} nao encontrado. Pode ser necessario reiniciar o terminal."
    }
}
Write-Host ""

# ─── Instalar uv ──────────────────────────────────────────────────────────────
Write-Host "-- Verificando uv..." -ForegroundColor Cyan
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Ok "uv ja instalado: $(uv --version)"
}
else {
    Write-Host "  Instalando uv..."
    try {
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
        $uvBin = Join-Path $env:USERPROFILE ".local\bin"
        if (Test-Path $uvBin) {
            $pathUser = [Environment]::GetEnvironmentVariable("Path", "User")
            if ($pathUser -notlike "*$uvBin*") {
                [Environment]::SetEnvironmentVariable("Path", "$pathUser;$uvBin", "User")
            }
            $env:Path += ";$uvBin"
        }
        if (Get-Command uv -ErrorAction SilentlyContinue) {
            Ok "uv instalado: $(uv --version)"
        }
    }
    catch {
        Aviso "Falha ao instalar uv: $_"
    }
}
Write-Host ""

# ─── Instalar pacotes Python ──────────────────────────────────────────────────
Write-Host "-- Instalando pacotes Python com uv..." -ForegroundColor Cyan
if (Get-Command uv -ErrorAction SilentlyContinue) {
    & uv sync
    Ok "Ambiente Python configurado."
}
else {
    Aviso "uv nao encontrado. Tente reiniciar o terminal."
}
Write-Host ""

# ─── Menu de Contexto ─────────────────────────────────────────────────────────
Write-Host "-- Registrando menu de contexto (clique-direito)..." -ForegroundColor Cyan
$InstallDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$regScript = Join-Path $InstallDir "context_menu\register_windows.ps1"
if (Test-Path $regScript) {
    try {
        & powershell -ExecutionPolicy Bypass -File $regScript -InstallDir $InstallDir
    }
    catch {
        Aviso "Nao foi possivel registrar o menu de contexto: $_"
        Aviso "Execute manualmente: powershell -ExecutionPolicy Bypass -File context_menu\register_windows.ps1"
    }
}
else {
    Aviso "Script de registro nao encontrado: $regScript"
}
Write-Host ""

# --- Conclusion ---
Write-Host "Install completed!" -ForegroundColor Cyan
Write-Host "Run: uv run isbn.py" -ForegroundColor White
Write-Host "Context menu: Right click in Explorer" -ForegroundColor Yellow
Write-Host "If tools are missing, restart your terminal." -ForegroundColor Gray
