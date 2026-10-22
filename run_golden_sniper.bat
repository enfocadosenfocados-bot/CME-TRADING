@echo off
title Golden Sniper Suite - 6 Activos Campeones en Horas de Oro
color 0A
cls
echo ===============================================================================
echo     GOLDEN SNIPER SUITE - 6 ACTIVOS CAMPEONES EN HORAS DE ORO
echo ===============================================================================
echo.

set PYTHON_CMD=
python --version >nul 2>&1 && set PYTHON_CMD=python
if "%PYTHON_CMD%"=="" (
    py -3 --version >nul 2>&1 && set PYTHON_CMD=py -3
)
if "%PYTHON_CMD%"=="" (
    py --version >nul 2>&1 && set PYTHON_CMD=py
)

if "%PYTHON_CMD%"=="" (
    echo [AVISO] Intentando instalar Python runtime automaticamente...
    py install 3.13
    py -3 --version >nul 2>&1 && set PYTHON_CMD=py -3
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR CRITICO] Python no esta instalado en el sistema.
    echo Abre PowerShell y ejecuta: py install 3.13
    pause
    exit /b 1
)

echo [*] Interprete detectado: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.
echo [*] Conectando a MetaTrader 5 y escaneando simbolos del broker...
echo.

%PYTHON_CMD% "%~dp0golden_sniper_bot.py" --daemon
if %errorlevel% neq 0 (
    echo.
    echo [!] El proceso se detuvo con codigo %errorlevel%.
    echo Revisa el mensaje superior para corregir la configuracion.
)
pause
