# Instalador PowerShell para CME Institutional Quant Suite
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "    INSTALADOR AUTOMATICO - CME INSTITUTIONAL QUANT TRADING SUITE" -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host ""

$pythonCmd = "python"
if (Get-Command "py" -ErrorAction SilentlyContinue) {
    $pythonCmd = "py -3.13"
}

Write-Host "[*] Verificando instalacion de Python..." -ForegroundColor Yellow
try {
    $ver = Invoke-Expression "$pythonCmd --version"
    Write-Host "[OK] $ver detectado." -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python no encontrado en el PATH. Instale Python 3.10+ desde https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

Write-Host "[*] Instalando dependencias de Python..." -ForegroundColor Yellow
Invoke-Expression "$pythonCmd -m pip install --upgrade pip"
Invoke-Expression "$pythonCmd -m pip install -r '$PSScriptRoot\requirements.txt'"

Write-Host ""
Write-Host "===============================================================================" -ForegroundColor Green
Write-Host "[EXITO] Entorno configurado correctamente." -ForegroundColor Green
Write-Host "Inicia el bot con: .\run_master_vps.bat" -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Green
