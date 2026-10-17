@echo off
title Instalador CME Quantitative Trading Suite
color 0A
cls
echo ===============================================================================
echo     INSTALADOR AUTOMATICO - CME INSTITUTIONAL QUANT TRADING SUITE
echo ===============================================================================
echo.

set PYTHON_CMD=python
py -3.13 --version >nul 2>&1 && set PYTHON_CMD=py -3.13
if "%PYTHON_CMD%"=="" set PYTHON_CMD=python

echo [*] Detectando interprete de Python...
%PYTHON_CMD% --version
if %errorlevel% neq 0 (
    echo [ERROR] No se encontro Python instalado en el sistema.
    echo Por favor instale Python 3.10 o superior marcando "Add Python to PATH".
    echo Descarga: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo [*] Instalando dependencias requeridas (MetaTrader5, pandas, numpy, requests, scipy)...
%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install -r "%~dp0requirements.txt"

if %errorlevel% neq 0 (
    echo [ADVERTENCIA] Ocurrio un error al instalar algunas librerias. Reintentando...
    %PYTHON_CMD% -m pip install MetaTrader5 pandas numpy requests scipy
)

echo.
echo ===============================================================================
echo [EXITO] Todas las librerias fueron instaladas correctamente.
echo Ya puedes ejecutar 'run_master_vps.bat' para iniciar la suite institucional.
echo ===============================================================================
echo.
pause
