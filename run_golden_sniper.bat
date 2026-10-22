@echo off
title Golden Sniper Suite - 6 Activos Campeones en Horas de Oro
color 0A
cls
echo ===============================================================================
echo     GOLDEN SNIPER SUITE - 6 ACTIVOS CAMPEONES EN HORAS DE ORO
echo ===============================================================================
echo.

set PYTHON_CMD=
py -3.12 --version >nul 2>&1 && set PYTHON_CMD=py -3.12
if "%PYTHON_CMD%"=="" (
    py -3.13 --version >nul 2>&1 && set PYTHON_CMD=py -3.13
)
if "%PYTHON_CMD%"=="" (
    py -3.11 --version >nul 2>&1 && set PYTHON_CMD=py -3.11
)
if "%PYTHON_CMD%"=="" (
    py -3.10 --version >nul 2>&1 && set PYTHON_CMD=py -3.10
)
if "%PYTHON_CMD%"=="" (
    python --version 2>&1 | findstr /R "3\.10 3\.11 3\.12 3\.13" >nul 2>&1 && set PYTHON_CMD=python
)

if "%PYTHON_CMD%"=="" (
    echo [AVISO] Instalando Python 3.12 compatible con MetaTrader 5...
    py install 3.12
    set PYTHON_CMD=py -3.12
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
