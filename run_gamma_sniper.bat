@echo off
title Gamma Exposure Sniper Suite - Walk-Forward Elite 12 Activos (CBOE + CME Obscura + Deribit)
color 0A
cls
echo ============================================================================================
echo   GAMMA EXPOSURE SNIPER SUITE - SELECCION ELITE WALK-FORWARD (ENE-JUL IS ^> JUL-HOY OOS)
echo   Regla Institucional: Maximo 1 Trade por Hora de Oro al Dia (One ^& Done) + Lote Minimo
echo ============================================================================================
echo.
echo   Activos, Magics, Filtros Walk-Forward y Ventanas de Oro (Hora Broker IC / Hora CDMX):
echo    01. XAUUSD [Oro Spot]     ^| Magic: 20269905 ^| 3 Filtros ^| Brk: 16h,03h,08h (MX: 07h,18h,23h)
echo    02. XAGUSD [Plata Spot]   ^| Magic: 20269906 ^| 2 Filtros ^| Brk: 17h,21h     (MX: 08h,12h)
echo    03. US30   [Dow Jones 30] ^| Magic: 20269904 ^| 1 Filtro  ^| Brk: 01h,23h     (MX: 16h,14h)
echo    04. US2000 [Russell 2000] ^| Magic: 20269903 ^| 2 Filtros ^| Brk: 17h,21h,20h (MX: 08h,12h,11h)
echo    05. USTEC  [Nasdaq 100]   ^| Magic: 20269902 ^| 2 Filtros ^| Brk: 22h,10h,23h (MX: 13h,01h,14h)
echo    06. USOIL  [Petroleo WTI] ^| Magic: 20269907 ^| 1 Filtro  ^| Brk: 22h,04h     (MX: 13h,19h)
echo    07. BTCUSD [Bitcoin]      ^| Magic: 20269911 ^| 3 Filtros ^| Brk: 21h,05h,18h (MX: 12h,20h,09h)
echo    08. US500  [S^&P 500]      ^| Magic: 20269901 ^| 2 Filtros ^| Brk: 17h,04h     (MX: 08h,19h)
echo    09. GBPUSD [Libra Cable]  ^| Magic: 20269909 ^| 2 Filtros ^| Brk: 07h,13h,17h (MX: 22h,04h,08h)
echo    10. AUDUSD [Aussie FX]    ^| Magic: 20269910 ^| 2 Filtros ^| Brk: 21h,13h,18h (MX: 12h,04h,09h)
echo    11. EURUSD [Euro FX]      ^| Magic: 20269908 ^| 3 Filtros ^| Brk: 09h,15h,23h (MX: 00h,06h,14h)
echo    12. ETHUSD [Ethereum]     ^| Magic: 20269912 ^| 2 Filtros ^| Brk: 08h,18h,14h (MX: 23h,09h,05h)
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
echo [*] Conectando a MetaTrader 5 e iniciando Gamma Exposure Sniper 24/7...
echo.

%PYTHON_CMD% "%~dp0gamma_sniper_bot.py" --daemon
if %errorlevel% neq 0 (
    echo.
    echo [!] El proceso se detuvo con codigo %errorlevel%.
)
pause
