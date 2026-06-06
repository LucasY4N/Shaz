@echo off
:: ============================================================
::  Shaz AI — Instalação no Windows
::  Resolve pyaudio sem precisar do Visual C++ Build Tools
:: ============================================================

echo.
echo  ⚡ Shaz AI — Setup Windows
echo  ============================================================
echo.

:: 1. Dependências principais (sem pyaudio)
echo [1/4] Instalando dependencias principais...
pip install -e ".[dev]"
if %errorlevel% neq 0 (
    echo ERRO: falha no pip install principal.
    pause & exit /b 1
)

:: 2. pyaudio via pipwin (wheel pré-compilado para Windows)
echo.
echo [2/4] Instalando pipwin...
pip install pipwin
if %errorlevel% neq 0 (
    echo AVISO: pipwin falhou. Tentando wheel direto...
    goto :wheel_fallback
)

echo [3/4] Instalando pyaudio via pipwin...
pipwin install pyaudio
if %errorlevel% neq 0 (
    goto :wheel_fallback
)
goto :done

:wheel_fallback
:: Fallback: baixar wheel pré-compilado do repositório não oficial
echo [3/4] Instalando pyaudio via wheel pre-compilado...
pip install pyaudio --only-binary=:all:
if %errorlevel% neq 0 (
    echo.
    echo  AVISO: pyaudio nao instalado automaticamente.
    echo  Para voz, instale manualmente:
    echo    1. Acesse: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
    echo    2. Baixe o .whl para sua versao do Python (cp314 = Python 3.14)
    echo    3. Execute: pip install PyAudio-0.2.14-cp314-cp314-win_amd64.whl
    echo.
    echo  O restante do Shaz AI funciona sem voz.
)

:done
echo.
echo [4/4] Verificando instalacao...
python -c "import motor, pymongo, pydantic, loguru, rich, typer; print('  OK - dependencias principais OK')"
python -c "import pyaudio; print('  OK - pyaudio OK')" 2>nul || echo   AVISO - pyaudio ausente (voz desabilitada)

echo.
echo  ============================================================
echo  ✅ Instalacao concluida!
echo.
echo  Proximos passos:
echo    1. Copie .env.example para .env e preencha suas chaves
echo    2. Inicie o MongoDB:  docker run -d -p 27017:27017 mongo:7
echo    3. Use a CLI:
echo         python main.py chat "Ola!"
echo         python main.py dashboard
echo  ============================================================
echo.
pause
