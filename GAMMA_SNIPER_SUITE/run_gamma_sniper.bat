@echo off
title Gamma Exposure Sniper Suite - 12 Activos Completos (CBOE + CME Obscura + Deribit)
color 0A
cls
echo ====================================================================================
echo   GAMMA EXPOSURE SNIPER SUITE - 12 ACTIVOS COMPLETOS (ITMATRIX / CBOE / CME / DERIBIT)
echo ====================================================================================
echo.
echo   Activos y Magics Institucionales:
echo    01. US500  [S^&P 500]      ^| Magic: 20269901 ^| CBOE _SPX / SPY 0DTE
echo    02. USTEC  [Nasdaq 100]   ^| Magic: 20269902 ^| CBOE QQQ / _NDX 0DTE
echo    03. US2000 [Russell 2000] ^| Magic: 20269903 ^| CBOE IWM / _RUT 0DTE
echo    04. US30   [Dow Jones 30] ^| Magic: 20269904 ^| CBOE DIA / _DJX 0DTE
echo    05. XAUUSD [Oro Spot]     ^| Magic: 20269905 ^| CBOE GLD + CME GC/GCVL Obscura
echo    06. XAGUSD [Plata Spot]   ^| Magic: 20269906 ^| CBOE SLV + CME SI/SIVL Obscura
echo    07. USOIL  [Petroleo WTI] ^| Magic: 20269907 ^| CBOE USO + CME CL/CLVL Obscura
echo    08. EURUSD [Euro FX]      ^| Magic: 20269908 ^| CME 6E/EUVL Obscura + CBOE FXE
echo    09. GBPUSD [Libra Cable]  ^| Magic: 20269909 ^| CME 6B/GBVL Obscura + CBOE FXB
echo    10. AUDUSD [Aussie FX]    ^| Magic: 20269910 ^| CME 6A/ADVL Obscura + CBOE FXA
echo    11. BTCUSD [Bitcoin]      ^| Magic: 20269911 ^| Deribit Native BTC + CBOE IBIT
echo    12. ETHUSD [Ethereum]     ^| Magic: 20269912 ^| Deribit Native ETH + CBOE ETHA
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
