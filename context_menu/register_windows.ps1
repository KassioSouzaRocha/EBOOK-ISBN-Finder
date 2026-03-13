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

# Localizar UV (Evitando ?. que não existe no PS 5.1)
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if ($uvCmd) {
    $uvPath = $uvCmd.Source
} else {
    $uvPath = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
    if (-not (Test-Path $uvPath)) { $uvPath = "uv" }
}

# ── DEFINIÇÃO DOS COMANDOS ───────────────────────────────────────────────────

# Caminho do script de execução
$isbnScript = Join-Path $InstallDir "isbn.py"

# Comando para arquivo único
# Explicação: cmd /c start powershell ... "Set-Location '$InstallDir'; & '$uvPath' run ..."
# Usamos & para garantir que o caminho do UV com espaços seja tratado como comando.
$cmdSomenteEsseItem = "cmd /c start /wait powershell -NoExit -ExecutionPolicy Bypass -Command " +
               "`"Set-Location '$InstallDir'; & '$uvPath' run '$isbnScript' --arquivo '%1'`""

# Comando para pasta (quando clica em diretório)
$cmdPasta = "cmd /c start /wait powershell -NoExit -ExecutionPolicy Bypass -Command " +
               "`"Set-Location '$InstallDir'; & '$uvPath' run '$isbnScript' --pasta '%V'`""

# Comando para pasta (quando clica em arquivo, processa o diretório pai)
$cmdPastaDoArquivo = "cmd /c start /wait powershell -NoExit -ExecutionPolicy Bypass -Command " +
                     "`"Set-Location '$InstallDir'; `$parent = Split-Path -Parent '%1'; & '$uvPath' run '$isbnScript' --pasta `$parent`""

# ── REGISTRO NO WINDOWS ──────────────────────────────────────────────────────

# Extensões suportadas
$extensoes = @(".pdf", ".epub", ".mobi")

try {
    # 1. Registro para PASTAS (Fundo da pasta e item da pasta)
    $chavesPasta = @(
        "HKCU:\Software\Classes\Directory\shell\RenomearISBN",
        "HKCU:\Software\Classes\Directory\Background\shell\RenomearISBN"
    )

    foreach ($chave in $chavesPasta) {
        New-Item -Path $chave -Force | Out-Null
        Set-ItemProperty -Path $chave -Name "(default)" -Value "Renomear pasta inteira com ISBN"
        Set-ItemProperty -Path $chave -Name "Icon"      -Value "imageres.dll,-5356"
        New-Item -Path "$chave\command" -Force | Out-Null
        Set-ItemProperty -Path "$chave\command" -Name "(default)" -Value $cmdPasta
    }
    Write-Host "✅ Menu registrado para pastas e subpastas." -ForegroundColor Green

    # 2. Registro para ARQUIVOS (Utilizando SystemFileAssociations para não quebrar o padrão)
    foreach ($ext in $extensoes) {
        # SystemFileAssociations permite adicionar menus sem mudar o ProgID/aplicativo padrão
        $baseChave = "HKCU:\Software\Classes\SystemFileAssociations\$ext\shell\RenomearISBN"
        
        New-Item -Path $baseChave -Force | Out-Null
        Set-ItemProperty -Path $baseChave -Name "(default)" -Value "Renomear com ISBN"
        Set-ItemProperty -Path $baseChave -Name "Icon"      -Value "imageres.dll,-5356"
        Set-ItemProperty -Path $baseChave -Name "SubCommands" -Value ""

        # Subação: "Somente esse item"
        $somenteChave = "$baseChave\shell\SomenteEsseItem"
        New-Item -Path $somenteChave -Force | Out-Null
        Set-ItemProperty -Path $somenteChave -Name "(default)" -Value "Somente esse item"
        Set-ItemProperty -Path $somenteChave -Name "Icon"      -Value "shell32.dll,-16769"
        New-Item -Path "$somenteChave\command" -Force | Out-Null
        Set-ItemProperty -Path "$somenteChave\command" -Name "(default)" -Value $cmdSomenteEsseItem

        # Subação: "Pasta inteira"
        $pastaChave = "$baseChave\shell\PastaInteira"
        New-Item -Path $pastaChave -Force | Out-Null
        Set-ItemProperty -Path $pastaChave -Name "(default)" -Value "Pasta inteira (diretório do arquivo)"
        Set-ItemProperty -Path $pastaChave -Name "Icon"      -Value "imageres.dll,-5356"
        New-Item -Path "$pastaChave\command" -Force | Out-Null
        Set-ItemProperty -Path "$pastaChave\command" -Name "(default)" -Value $cmdPastaDoArquivo

        Write-Host "✅ Menu registrado com segurança para $ext." -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "Configuração do registro concluída com sucesso!" -ForegroundColor Cyan
} catch {
    Write-Error "Erro ao modificar o registro: $_"
    exit 1
}
