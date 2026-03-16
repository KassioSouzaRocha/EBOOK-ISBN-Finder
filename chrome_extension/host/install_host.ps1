$ErrorActionPreference = "Stop"

function Ok { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Aviso { param($msg) Write-Host "  [!]  $msg" -ForegroundColor Yellow }
function Erro { param($msg) Write-Host "  [X]  $msg" -ForegroundColor Red; exit 1 }

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Instalando Host Nativo (Chrome/Edge)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

$DirScript = Split-Path -Parent $MyInvocation.MyCommand.Path
$WrapperPath = Join-Path $DirScript "isbn_wrapper.bat"
$HostScript = Join-Path $DirScript "isbn_native_host.py"

# Cria um wrapper .bat para chamar o python no Windows
$PythonVenv = Join-Path (Split-Path -Parent (Split-Path -Parent $DirScript)) ".venv\Scripts\python.exe"

$BatContent = @"
@echo off
set "PYTHON_EXE=$PythonVenv"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"
"%PYTHON_EXE%" "$HostScript"
"@
Set-Content -Path $WrapperPath -Value $BatContent -Encoding UTF8

Write-Host "  1. Abra o Chrome/Edge, va em Extensoes e ative 'Modo do Desenvolvedor'."
Write-Host "  2. Carregue a pasta 'chrome_extension' (sem compactacao)."
Write-Host "  3. Copie o ID gerado pelo navegador."
Write-Host ""
$extId = Read-Host "  -> Cole aqui o ID da extensao (ou digite N para cancelar)"
$extId = $extId.Trim()

if ($extId -eq "N" -or $extId -eq "n" -or $extId -eq "") {
    Aviso "Instalacao do Native Host cancelada."
    exit
}

$ManifestPath = Join-Path $DirScript "com.kassio.isbn_renamer.json"
$ManifestContent = @"
{
  "name": "com.kassio.isbn_renamer",
  "description": "Host nativo para o ISBN Renamer",
  "path": "$($WrapperPath -replace '\\', '\\')",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://$extId/"
  ]
}
"@

Set-Content -Path $ManifestPath -Value $ManifestContent -Encoding UTF8

# Registrando no Registry
$RegistryPaths = @(
    "HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.kassio.isbn_renamer",
    "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\com.kassio.isbn_renamer"
)

foreach ($RPath in $RegistryPaths) {
    if (-not (Test-Path $RPath)) {
        New-Item -Path $RPath -Force | Out-Null
    }
    Set-ItemProperty -Path $RPath -Name "(Default)" -Value $ManifestPath
}

Ok "Host Nativo registrado com sucesso no Google Chrome e Edge."
Write-Host ""
