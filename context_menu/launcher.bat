@echo off
setlocal
:: Launcher para EBOOK-ISBN-Finder
:: Argumentos: %1=uv_path, %2=script_path, %3=mode, %4=target

set "UV_EXE=%~1"
set "SCRIPT_PY=%~2"
set "MODE=%~3"
set "TARGET=%~4"

:: Extrair diretorio do script para garantir que o uv ache o pyproject.toml
set "PROJECT_ROOT=%~dp2"

echo -----------------------------------------------------------------------------
echo ISBN Renamer Launcher
echo -----------------------------------------------------------------------------
echo Projeto: %PROJECT_ROOT%
echo Modo:    %MODE%
echo Alvo:    %TARGET%
echo -----------------------------------------------------------------------------

:: Mudar para o diretorio do projeto
cd /d "%PROJECT_ROOT%"

:: Executar com uv
"%UV_EXE%" run "%SCRIPT_PY%" "%MODE%" "%TARGET%"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] Ocorreu um erro durante a execucao.
    pause
)
