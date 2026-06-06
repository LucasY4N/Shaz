@echo off
title Shaz AI - Build EXE
chcp 65001 >nul

echo ============================================
echo     Shaz AI - Gerando ShazBot.exe
echo ============================================
echo.

:: Verificar PyInstaller
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [1/3] Instalando PyInstaller...
    pip install pyinstaller -q
) else (
    echo [1/3] PyInstaller encontrado
)

:: Verificar dependencias
echo [2/3] Verificando dependencias...
python -c "import shaz.utils.installer; shaz.utils.installer.DependencyChecker.run_full_check()" 2>nul

:: Build
echo.
echo [3/3] Gerando executavel...
echo Isso pode levar varios minutos...
echo.

pyinstaller build.spec --noconfirm

if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo     Executavel gerado com sucesso!
    echo ============================================
    echo.
    echo Arquivo: dist\ShazBot.exe
    echo Tamanho: 
    for %%I in (dist\ShazBot.exe) do echo %%~zI bytes
    echo.
    echo Para executar:
    echo   dist\ShazBot.exe
    echo.
) else (
    echo [ERROR] Falha ao gerar executavel
    echo Verifique os logs acima.
)

pause