@echo off
title CME Institutional Quant Suite - IC Markets MT5
color 0B
cls
echo ===============================================================================
echo     CME INSTITUTIONAL QUANT SUITE - IC MARKETS MT5 AUTONOMOUS TRADER
echo ===============================================================================
echo.
echo  Seleccione la estrategia cuantitativa que desea ejecutar:
echo.
echo   [G] GOLDEN SNIPER : 6 ACTIVOS CAMPEONES EN HORAS DE ORO (Lote Minimo + 50%% Parcial TP1) [RECOMENDADO]
echo   [S] ALL SNIPER    : SUITE TOTAL CON TRINITY SNIPER (Apertura NY 13:30-15:30 + Hedges + Stat-Arb + COT)
echo   [T] TRINITY SNIPER: Solo Trinity Apertura NY (Sin Hedges ni Arbitrajes - 1 Trade/Dia)
echo   [1] TRINITY [LNY] : Sesion Londres + Nueva York (07:00 a 21:00 UTC) [Magic: 71YY00]
echo   [2] TRINITY [NY]  : Sesion Solo Nueva York      (13:00 a 21:00 UTC) [Magic: 72YY00]
echo   [3] TRINITY DUAL  : Ambas Sesiones en Paralelo                      [Magics 71/72]
echo   [4] STAT-ARB      : Multi-Par Cointegrado (4 Pares Market-Neutral)  [Magic: 73YY00]
echo   [5] COT SQUEEZE   : Macro COT Squeeze & Momentum (11 Activos CME)   [Magic: 74YY00]
echo   [6] HEDGES CME    : 6 Coberturas Institucionales (CVOL, Roll, etc)  [Magic: 75YY00]
echo   [7] SUITE MASTER TOTAL (Trinity LNY+NY Dual + Hedges + Stat-Arb + COT)
echo   [8] SUITE MASTER LNY   (Trinity LNY + Stat-Arb + COT + 6 Hedges)
echo   [9] SUITE MASTER NY    (Trinity NY  + Stat-Arb + COT + 6 Hedges)
echo   [A] AUDITORIA EN VIVO  (Escanear todo el universo sin enviar ordenes)
echo   [0] SALIR
echo.
set /p opt=Ingrese su opcion [G]: 

if /i "%opt%"=="G" goto optG
if /i "%opt%"=="S" goto optS
if /i "%opt%"=="T" goto optT
if /i "%opt%"=="1" goto opt1
if /i "%opt%"=="2" goto opt2
if /i "%opt%"=="3" goto opt3
if /i "%opt%"=="4" goto opt4
if /i "%opt%"=="5" goto opt5
if /i "%opt%"=="6" goto opt6
if /i "%opt%"=="7" goto opt7
if /i "%opt%"=="8" goto opt8
if /i "%opt%"=="9" goto opt9
if /i "%opt%"=="A" goto optA
if /i "%opt%"=="0" goto opt0
goto optG

:optG
cls
echo ===============================================================================
echo   INICIANDO TRINITY GOLDEN SNIPER (6 ACTIVOS CAMPEONES EN HORAS DE ORO)
echo   Activos: US30, USTEC, US2000, XAUUSD, GBPUSD, BTCUSD
echo   Lotaje: Minimo Permitido Divisible (50%% Parcial @ TP1 + Runner Trailing @ TP2)
echo ===============================================================================
py -3.13 "%~dp0master_institutional_bot.py" --mode GOLDEN_SNIPER --daemon
pause
goto :eof

:optS
cls
echo Iniciando SUITE TOTAL CON TRINITY SNIPER (Trinity Sniper + Hedges + Stat-Arb + COT)...
py -3.13 "%~dp0master_institutional_bot.py" --mode ALL_SNIPER --daemon
pause
goto :eof

:optT
cls
echo Iniciando Solo Trinity Apertura NY SNIPER (13:30-15:30 UTC - 1 Trade/Dia)...
py -3.13 "%~dp0master_institutional_bot.py" --mode TRINITY_SNIPER --daemon
pause
goto :eof

:opt1
cls
echo Iniciando Trinity Version LNY (Londres + NY: 07-21 UTC) en modo continuo...
py -3.13 "%~dp0master_institutional_bot.py" --mode TRINITY_LNY --daemon
pause
goto :eof

:opt2
cls
echo Iniciando Trinity Version NY (Solo NY: 13-21 UTC) en modo continuo...
py -3.13 "%~dp0master_institutional_bot.py" --mode TRINITY_NY --daemon
pause
goto :eof

:opt3
cls
echo Iniciando Trinity Version Dual (LNY + NY) en modo continuo...
py -3.13 "%~dp0master_institutional_bot.py" --mode TRINITY_DUAL --daemon
pause
goto :eof

:opt4
cls
echo Iniciando Stat-Arb Multi-Pair Trading en modo continuo...
py -3.13 "%~dp0master_institutional_bot.py" --mode PAIR --daemon
pause
goto :eof

:opt5
cls
echo Iniciando Macro COT Squeeze Engine en modo continuo...
py -3.13 "%~dp0master_institutional_bot.py" --mode COT --daemon
pause
goto :eof

:opt6
cls
echo Iniciando 6 Coberturas Institucionales CME (Hedges) en modo continuo...
py -3.13 "%~dp0master_institutional_bot.py" --mode HEDGES --daemon
pause
goto :eof

:opt7
cls
echo Iniciando SUITE MASTER TOTAL (Todas las estrategias integradas) 24/7...
py -3.13 "%~dp0master_institutional_bot.py" --mode ALL_DUAL --daemon
pause
goto :eof

:opt8
cls
echo Iniciando SUITE MASTER LNY (Trinity LNY + Stat-Arb + COT + 6 Hedges) 24/7...
py -3.13 "%~dp0master_institutional_bot.py" --mode ALL_LNY --daemon
pause
goto :eof

:opt9
cls
echo Iniciando SUITE MASTER NY (Trinity NY + Stat-Arb + COT + 6 Hedges) 24/7...
py -3.13 "%~dp0master_institutional_bot.py" --mode ALL_NY --daemon
pause
goto :eof

:optA
cls
echo Ejecutando Auditoria Cuantitativa en Vivo (Modo Simulacion)...
py -3.13 "%~dp0master_institutional_bot.py" --audit
pause
goto :eof

:opt0
exit
