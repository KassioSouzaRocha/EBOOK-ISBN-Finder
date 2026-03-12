# register_windows.ps1
# ─────────────────────────────────────────────────────────────────────────────
# Registra "Renomear com ISBN" no menu de contexto do Windows Explorer
# Chamado automaticamente pelo install.ps1
# ─────────────────────────────────────────────────────────────────────────────

param(
    [string]$InstallDir = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
)

$uvPath   = (Get-Command uv -ErrorAction SilentlyContinue)?.Source
if (-not $uvPath) { $uvPath = "uv" }   # espera estar no PATH

# Comando executado ao clicar no menu
# %V = caminho da pasta selecionada (Explorer shell verb)
$comando = "cmd /c start powershell -NoExit -ExecutionPolicy Bypass -Command " +
           "\"cd '$InstallDir'; $uvPath run isbn.py --pasta '%V'\""

$chaveBase = "HKCU:\Software\Classes\Directory\shell\RenomearISBN"

try {
    # Cria (ou sobrescreve) a entrada no registro
    New-Item -Path $chaveBase -Force | Out-Null
    Set-ItemProperty -Path $chaveBase -Name "(default)" -Value "Renomear com ISBN"
    Set-ItemProperty -Path $chaveBase -Name "Icon" -Value "imageres.dll,-5356"

    New-Item -Path "$chaveBase\command" -Force | Out-Null
    Set-ItemProperty -Path "$chaveBase\command" -Name "(default)" -Value $comando

    Write-Host "✅ Menu de contexto registrado com sucesso!" -ForegroundColor Green
    Write-Host "   Clique-direito em qualquer pasta no Explorer -> 'Renomear com ISBN'"
} catch {
    Write-Error "Falha ao registrar no registro: $_"
    exit 1
}
