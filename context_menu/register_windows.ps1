# register_windows.ps1
# ─────────────────────────────────────────────────────────────────────────────
# Registra "Renomear com ISBN" no menu de contexto do Windows Explorer
# Suporta:
#   - Clique-direito em ARQUIVO PDF/EPUB/MOBI → "Somente esse item" (--arquivo)
#   - Clique-direito em PASTA  → processa todos os livros da pasta (--pasta)
# Chamado automaticamente pelo install.ps1
# ─────────────────────────────────────────────────────────────────────────────

param(
    [string]$InstallDir = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
)

$uvPath = (Get-Command uv -ErrorAction SilentlyContinue)?.Source
if (-not $uvPath) { $uvPath = "uv" }   # espera estar no PATH

# ── 1. MENU PARA ARQUIVOS: "Somente esse item" ───────────────────────────────
$cmdSomenteEsseItem = "cmd /c start powershell -NoExit -ExecutionPolicy Bypass -Command " +
               "\"cd '$InstallDir'; $uvPath run isbn.py --arquivo '%1'\""

# ── 2. MENU PARA PASTAS ──────────────────────────────────────────────────────
$cmdPasta    = "cmd /c start powershell -NoExit -ExecutionPolicy Bypass -Command " +
               "\"cd '$InstallDir'; $uvPath run isbn.py --pasta '%V'\""
$chavePasta  = "HKCU:\Software\Classes\Directory\shell\RenomearISBN"

# Extensões que receberão a entrada no menu de contexto
$extensoes = @(".pdf", ".epub", ".mobi")

try {
    # --- Pasta ---
    New-Item -Path $chavePasta -Force | Out-Null
    Set-ItemProperty -Path $chavePasta -Name "(default)" -Value "Renomear pasta inteira com ISBN"
    Set-ItemProperty -Path $chavePasta -Name "Icon"      -Value "imageres.dll,-5356"
    New-Item -Path "$chavePasta\command" -Force | Out-Null
    Set-ItemProperty -Path "$chavePasta\command" -Name "(default)" -Value $cmdPasta

    Write-Host "✅ Menu registrado para pastas." -ForegroundColor Green

    # --- Arquivos: "Somente esse item" ---
    foreach ($ext in $extensoes) {
        # Garante que a extensão tem uma chave ProgID associada
        $extChave    = "HKCU:\Software\Classes\$ext"
        $progId      = "ISBNRenamer$($ext.TrimStart('.'))"

        New-Item -Path $extChave -Force | Out-Null
        Set-ItemProperty -Path $extChave -Name "(default)" -Value $progId

        # Adiciona submenu pai "Renomear com ISBN"
        $submenuChave = "HKCU:\Software\Classes\$progId\shell\RenomearISBN"
        New-Item -Path $submenuChave -Force | Out-Null
        Set-ItemProperty -Path $submenuChave -Name "(default)" -Value "Renomear com ISBN"
        Set-ItemProperty -Path $submenuChave -Name "Icon"      -Value "imageres.dll,-5356"
        Set-ItemProperty -Path $submenuChave -Name "SubCommands" -Value ""

        # Subação: "Somente esse item"
        $somenteChave = "HKCU:\Software\Classes\$progId\shell\RenomearISBN\shell\SomenteEsseItem"
        New-Item -Path $somenteChave -Force | Out-Null
        Set-ItemProperty -Path $somenteChave -Name "(default)" -Value "Somente esse item"
        Set-ItemProperty -Path $somenteChave -Name "Icon"      -Value "shell32.dll,-16769"
        New-Item -Path "$somenteChave\command" -Force | Out-Null
        Set-ItemProperty -Path "$somenteChave\command" -Name "(default)" -Value $cmdSomenteEsseItem

        # Subação: "Pasta inteira" (atalho alternativo ao clicar em arquivo)
        $pastaChave = "HKCU:\Software\Classes\$progId\shell\RenomearISBN\shell\PastaInteira"
        New-Item -Path $pastaChave -Force | Out-Null
        Set-ItemProperty -Path $pastaChave -Name "(default)" -Value "Pasta inteira (diretório do arquivo)"
        Set-ItemProperty -Path $pastaChave -Name "Icon"      -Value "imageres.dll,-5356"
        New-Item -Path "$pastaChave\command" -Force | Out-Null
        # Usa %~dp1 para pegar o diretório do arquivo selecionado
        $cmdPastaDoArquivo = "cmd /c start powershell -NoExit -ExecutionPolicy Bypass -Command " +
                             "\"cd '$InstallDir'; $uvPath run isbn.py --pasta (Split-Path -Parent '%1')\""
        Set-ItemProperty -Path "$pastaChave\command" -Name "(default)" -Value $cmdPastaDoArquivo

        Write-Host "✅ Menu com 'Somente esse item' registrado para $ext." -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "Menu de contexto configurado com sucesso!" -ForegroundColor Cyan
    Write-Host "  Clique-direito em PDF/EPUB/MOBI → 'Renomear com ISBN' → 'Somente esse item'"
    Write-Host "  Clique-direito em PDF/EPUB/MOBI → 'Renomear com ISBN' → 'Pasta inteira'"
    Write-Host "  Clique-direito em PASTA         → 'Renomear pasta inteira com ISBN'"
} catch {
    Write-Error "Falha ao registrar no registro: $_"
    exit 1
}
