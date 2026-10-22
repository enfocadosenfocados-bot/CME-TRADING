@echo off
title Golden Sniper Suite - 6 Activos Campeones en Horas de Oro
color 0A
cls
echo ===============================================================================
echo     GOLDEN SNIPER SUITE - 6 ACTIVOS CAMPEONES EN HORAS DE ORO
echo ===============================================================================
echo.

set PYTHON_CMD=
py -3.13 --version >nul 2>&1 && set PYTHON_CMD=py -3.13
if "%PYTHON_CMD%"=="" (
    py -3 --version >nul 2>&1 && set PYTHON_CMD=py -3
)
if "%PYTHON_CMD%"=="" (
    python --version >nul 2>&1 && set PYTHON_CMD=python
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR CRITICO] Python no esta detectado en el PATH de Windows.
    echo.
    echo Para solucionarlo:
    echo 1. Abre el instalador de Python descargado en la VPS.
    echo 2. Marca la casilla "Add python.exe to PATH".
    echo 3. O ejecuta 'install.bat' para configurar el entorno.
    echo.
    pause
    exit /b 1
)

echo [*] Interprete detectado: %PYTHON_CMD%
echo [*] Conectando a MetaTrader 5 y escaneando simbolos del broker...
echo.

%PYTHON_CMD% "%~dp0golden_sniper_bot.py" --daemon
if %errorlevel% neq 0 (
    echo.
    echo [!] El proceso se detuvo con codigo %errorlevel%.
    echo Revisa el mensaje superior para corregir la configuracion.
)
pause
