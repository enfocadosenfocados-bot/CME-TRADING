@echo off
title Alpha Champions Suite - 6 Estrategias Ganadoras No-Trinity
color 0B
cls
echo ===============================================================================
echo     ALPHA CHAMPIONS SUITE - 6 ESTRATEGIAS GANADORAS NO-TRINITY
echo ===============================================================================
echo.
echo  Estrategias y Activos:
echo   1. Gold XAUUSD Sniper Alpha            (Magic: 20262104) - 13:00 Broker (10:00 UTC)
echo   2. DAX40 (DE40) Momentum Engine        (Magic: 20261103) - 13:00 Broker (10:00 UTC)
echo   3. Forex EURUSD Trend Engine           (Magic: 20261106) - 13:00 Broker (10:00 UTC)
echo   4. Cable GBPUSD Scalper Alpha          (Magic: 20262105) - 13:00 Broker (10:00 UTC)
echo   5. Macro COT: Russell 2000 Squeeze     (Magic: 20261024) - 19:00 Broker (16:00 UTC)
echo   6. Stat-Arb Par 2: US30 / US2000       (Magic: 20268803) - 20:00-00:00 Broker
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
echo [*] Conectando a MetaTrader 5 e iniciando escaneo en VPS...
echo.

%PYTHON_CMD% "%~dp0alpha_champions_bot.py" --daemon
if %errorlevel% neq 0 (
    echo.
    echo [!] El proceso se detuvo con codigo %errorlevel%.
)
pause
