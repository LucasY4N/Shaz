@echo off
title Shaz AI - Instalador Windows
chcp 65001 >nul

echo ============================================
echo        Shaz AI - Instalador Windows
echo ============================================
echo.

:: Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python nao encontrado!
    echo Baixe Python 3.11+ em: https://python.org/downloads
    pause
    exit /b 1
)

python --version
echo.

:: Verificar pip
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] pip nao encontrado!
    pause
    exit /b 1
)

:: Atualizar pip
echo [1/4] Atualizando pip...
python -m pip install --upgrade pip -q
echo.

:: Instalar dependencias
echo [2/4] Instalando dependencias principais...
pip install -e ".[full]" --quiet
if %errorlevel% neq 0 (
    echo [WARNING] Algumas dependencias podem nao ter sido instaladas.
)
echo.

:: Instalar pyaudio (Windows)
echo [3/4] Instalando pyaudio...
pip install pipwin -q
pipwin install pyaudio -q 2>nul
if %errorlevel% neq 0 (
    echo [INFO] pyaudio nao instalado via pipwin.
    echo Tentando metodo alternativo...
    pip install pyaudio -q 2>nul
)
echo.

:: Verificar instalacao
echo [4/4] Verificando instalacao...
python -c "import sys; print(f'Python {sys.version}')" 2>nul
python -c "import rich; print('rich: OK')" 2>nul
python -c "import dotenv; print('dotenv: OK')" 2>nul
python -c "import httpx; print('httpx: OK')" 2>nul

echo.
echo ============================================
echo     Instalacao concluida!
echo ============================================
echo.
echo Para iniciar o Shaz AI:
echo   python main.py            (Modo Desktop)
echo   python main.py --cli      (Modo Terminal)
echo   python main.py --install  (Verificar dependencias)
echo.
echo Configure sua chave de API no arquivo .env
echo (copie .env.example para .env e edite)
echo.
pause