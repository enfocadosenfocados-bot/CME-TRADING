@echo off
title Golden Sniper Suite - 6 Activos Campeones en Horas de Oro
color 0A
cls
echo ===============================================================================
echo     GOLDEN SNIPER SUITE - 6 ACTIVOS CAMPEONES EN HORAS DE ORO
echo ===============================================================================
echo.
echo  Activos:
echo   - GS_US30   (Dow Jones 30)    | Magic: 880100 | Lote: 0.20 | 17:00 y 22:00 Broker
echo   - GS_USTEC  (Nasdaq 100)     | Magic: 880200 | Lote: 0.20 | 17:00 Broker
echo   - GS_US2000 (Russell 2000)   | Magic: 880300 | Lote: 2.00 | 16:00 a 18:00 Broker
echo   - GS_XAUUSD (Gold / Oro)     | Magic: 880400 | Lote: 0.02 | 05:00 y 19:00 Broker
echo   - GS_GBPUSD (British Pound)  | Magic: 880500 | Lote: 0.02 | 05:00 y 16:00 Broker
echo   - GS_BTCUSD (Bitcoin)        | Magic: 880600 | Lote: 0.02 | 16:00 y 03:00 Broker
echo.
echo  Iniciando ejecucion continua 24/7 en VPS...
echo.
py -3.13 "%~dp0golden_sniper_bot.py" --daemon
pause
