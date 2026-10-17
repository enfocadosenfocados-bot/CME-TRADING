@echo off
title CME Advanced Quantitative Hedges - IC Markets MT5
color 0A
cls

set PYTHON_CMD=python
py -3.13 --version >nul 2>&1 && set PYTHON_CMD=py -3.13
if "%PYTHON_CMD%"=="" set PYTHON_CMD=python

echo ===============================================================================
echo     CME ADVANCED INSTITUTIONAL HEDGES - IC MARKETS MT5 AUTONOMOUS TRADER
echo ===============================================================================
echo.
echo  Seleccione el modo operativo:
echo.
echo   [1] EJECUCION CONTINUA 24/7 EN VPS (Escaneo cada 30 segundos con TP/SL/BE/Trailing)
echo   [2] AUDITORIA EN VIVO (Simulacion de un ciclo sin enviar ordenes)
echo   [3] EJECUCION DE UN SOLO CICLO REAL
echo   [4] SALIR
echo.
set /p opt=Ingrese su opcion (1-4): 

if "%opt%"=="1" goto opt1
if "%opt%"=="2" goto opt2
if "%opt%"=="3" goto opt3
if "%opt%"=="4" goto opt4
goto opt1

:opt1
cls
echo Iniciando 6 Estrategias con Hedges en modo continuo 24/7 en VPS...
%PYTHON_CMD% "%~dp0strategy_institutional_hedges.py" --daemon
pause
goto :eof

:opt2
cls
echo Ejecutando Auditoria Cuantitativa en Vivo (Modo Simulacion)...
%PYTHON_CMD% "%~dp0strategy_institutional_hedges.py" --audit
pause
goto :eof

:opt3
cls
echo Ejecutando un solo ciclo real...
%PYTHON_CMD% "%~dp0strategy_institutional_hedges.py" --run-once
pause
goto :eof

:opt4
exit
