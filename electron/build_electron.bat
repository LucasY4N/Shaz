@echo off
:: ============================================================
::  Shaz OS — Build EXE com Electron
::  Execute este arquivo para gerar o instalador Windows
:: ============================================================

title Shaz OS — Build Electron
color 0D

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║       SHAZ OS — BUILD ELECTRON EXE      ║
echo  ║            NEXUS v3.0                    ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Vai para o diretório do script (pasta electron/)
cd /d "%~dp0"

:: ── 1. Verifica Node.js ───────────────────────────────────────
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Node.js nao encontrado!
    echo        Baixe em: https://nodejs.org
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('node --version') do set NODE_VER=%%v
echo [OK] Node.js %NODE_VER% detectado

:: ── 2. Instala dependências ───────────────────────────────────
echo.
echo [1/3] Instalando dependencias Electron...
call npm install
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao instalar dependencias!
    pause
    exit /b 1
)
echo [OK] Dependencias instaladas

:: ── 3. Cria pasta de assets se nao existir ───────────────────
if not exist "assets" mkdir assets
echo [INFO] Pasta assets/ pronta

:: ── 4. Gera o build ──────────────────────────────────────────
echo.
echo [2/3] Gerando EXE Windows...
call npm run build
if %errorlevel% neq 0 (
    echo [ERRO] Falha no build!
    echo        Verifique os logs acima.
    pause
    exit /b 1
)

:: ── 5. Resultado ─────────────────────────────────────────────
echo.
echo [3/3] Build concluido!
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║  EXE gerado em:                          ║
echo  ║  electron\dist\Shaz OS-win32-x64\        ║
echo  ║                                          ║
echo  ║  Execute "Shaz OS.exe" para abrir!       ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Abre a pasta dist no Explorer
if exist "dist" (
    explorer "dist"
)

pause
