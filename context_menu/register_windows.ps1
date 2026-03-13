# register_windows.ps1
# -----------------------------------------------------------------------------
# Registra "Renomear com ISBN" no menu de contexto do Windows Explorer
# --------------------------------─────────────────────────────────────────────

param(
    [string]$InstallDir = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
)

# 1. Caminhos Absolutos
$uvPath = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uvPath) { $uvPath = Join-Path $env:USERPROFILE ".local\bin\uv.exe" }
if (-not (Test-Path $uvPath)) { $uvPath = "uv.exe" }

$isbnScript = Join-Path $InstallDir "isbn.py"
$launcher   = Join-Path $InstallDir "context_menu\launcher.bat"

Write-Host "--- Configurações ---"
Write-Host "UV:       $uvPath"
Write-Host "Script:   $isbnScript"
Write-Host "Launcher: $launcher"

# Escapar caminhos para o arquivo .reg (barras invertidas duplas)
$uvR       = $uvPath.Replace("\", "\\")
$scriptR   = $isbnScript.Replace("\", "\\")
$launcherR = $launcher.Replace("\", "\\")

# ── DEFINIÇÃO DOS COMANDOS ───────────────────────────────────────────────────
# O comando para o registro deve ter aspas internas escapadas com \
$cmdSomente = "`"$launcherR`" `"$uvR`" `"$scriptR`" --arquivo `"%1`"".Replace('"', '\"')
$cmdPasta   = "`"$launcherR`" `"$uvR`" `"$scriptR`" --pasta `"%V`"".Replace('"', '\"')
$cmdPai     = "`"$launcherR`" `"$uvR`" `"$scriptR`" --pasta `"%1\\..`"".Replace('"', '\"')

# ── GERAR ARQUIVO .REG ───────────────────────────────────────────────────────
$regFile = Join-Path $env:TEMP "isbn_menu.reg"
$header = "Windows Registry Editor Version 5.00`r`n"
$content = $header

# Limpeza
$content += "[-HKEY_CURRENT_USER\Software\Classes\*\shell\RenomearISBN]`r`n"
$content += "[-HKEY_CURRENT_USER\Software\Classes\Folder\shell\RenomearISBN]`r`n"
$content += "[-HKEY_CURRENT_USER\Software\Classes\Directory\Background\shell\RenomearISBN]`r`n"

# Registro de Pastas
$content += @"

[HKEY_CURRENT_USER\Software\Classes\Folder\shell\RenomearISBN]
"MUIVerb"="Renomear pasta inteira com ISBN"
"Icon"="imageres.dll,-5356"

[HKEY_CURRENT_USER\Software\Classes\Folder\shell\RenomearISBN\command]
@="$cmdPasta"

[HKEY_CURRENT_USER\Software\Classes\Directory\Background\shell\RenomearISBN]
"MUIVerb"="Renomear pasta inteira com ISBN"
"Icon"="imageres.dll,-5356"

[HKEY_CURRENT_USER\Software\Classes\Directory\Background\shell\RenomearISBN\command]
@="$cmdPasta"

"@

# Adicionar extensões específicas
$extensoes = @(".pdf", ".epub", ".mobi")
foreach ($ext in $extensoes) {
    $baseKey = "HKEY_CURRENT_USER\Software\Classes\SystemFileAssociations\$ext\shell\RenomearISBN"
    $content += @"

[-$baseKey]
[$baseKey]
"MUIVerb"="Renomear com ISBN"
"Icon"="imageres.dll,-5356"
"SubCommands"=""

[$baseKey\shell\SomenteItem]
"MUIVerb"="Somente esse item"
"Icon"="shell32.dll,-16769"

[$baseKey\shell\SomenteItem\command]
@="$cmdSomente"

[$baseKey\shell\PastaInteira]
"MUIVerb"="Pasta inteira"
"Icon"="imageres.dll,-5356"

[$baseKey\shell\PastaInteira\command]
@="$cmdPai"
"@
}

# Salvar como UTF-16 LE com BOM (requerido pelo REG.EXE em alguns sistemas)
[System.IO.File]::WriteAllText($regFile, $content, [System.Text.Encoding]::Unicode)

Write-Host "--- Importando registro ---"
$process = Start-Process reg.exe -ArgumentList "import", "`"$regFile`"" -Wait -PassThru
if ($process.ExitCode -eq 0) {
    Write-Host "   [OK] Registro importado com sucesso!" -ForegroundColor Green
} else {
    Write-Host "   [ERRO] Falha ao importar registro (Erro: $($process.ExitCode))" -ForegroundColor Red
}

Remove-Item $regFile -ErrorAction SilentlyContinue
