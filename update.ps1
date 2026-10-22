# One-Click CME Quant Bot Updater from GitHub
$dest = "C:\CME_Quant_Bot"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$zip = "$env:TEMP\cme_repo.zip"
$ext = "$env:TEMP\cme_ext"

Write-Host "Descargando la suite mas reciente desde GitHub..." -ForegroundColor Cyan
Invoke-WebRequest -Uri "https://github.com/enfocadosenfocados-bot/CME-TRADING/archive/refs/heads/main.zip" -OutFile $zip

Write-Host "Descomprimiendo y actualizando archivos en $dest..." -ForegroundColor Cyan
Expand-Archive -Path $zip -DestinationPath $ext -Force
Copy-Item "$ext\CME-TRADING-main\*" -Destination $dest -Recurse -Force

Remove-Item $zip -Force -ErrorAction SilentlyContinue
Remove-Item $ext -Recurse -Force -ErrorAction SilentlyContinue

# MetaTrader 5 solo es compatible con Python 3.10, 3.11, 3.12 o 3.13 (Python 3.15 experimental no tiene soporte)
Write-Host "Verificando version compatible de Python para MetaTrader 5..." -ForegroundColor Cyan
$pyCmd = $null

foreach ($ver in @("-3.12", "-3.13", "-3.11", "-3.10")) {
    try {
        $out = & py $ver --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $out -match "Python 3\.(10|11|12|13)") {
            $pyCmd = "py $ver"
            break
        }
    } catch {}
}

if (-not $pyCmd) {
    try {
        $out = & python --version 2>&1
        if ($out -match "Python 3\.(10|11|12|13)") {
            $pyCmd = "python"
        }
    } catch {}
}

# Si no hay version compatible (ej. el sistema tiene 3.15), instalar Python 3.12 automaticamente
if (-not $pyCmd) {
    Write-Host "Python 3.15 experimental detectado. MetaTrader 5 requiere Python 3.12." -ForegroundColor Yellow
    Write-Host "Descargando e instalando Python 3.12 oficial (100% compatible)..." -ForegroundColor Cyan
    & py install 3.12
    $pyCmd = "py -3.12"
}

if ($pyCmd) {
    Write-Host "Instalando dependencias de MetaTrader 5 con $pyCmd..." -ForegroundColor Cyan
    & cmd /c "$pyCmd -m pip install --upgrade pip --quiet"
    & cmd /c "$pyCmd -m pip install -r `"$dest\requirements.txt`""
} else {
    Write-Host "[ERROR] Por favor ejecuta 'py install 3.12' para instalar la version compatible." -ForegroundColor Red
}

# Crear acceso directo en el escritorio
try {
    $WshShell = New-Object -ComObject WScript.Shell
    $Desktop = [Environment]::GetFolderPath("Desktop")
    
    $Shortcut = $WshShell.CreateShortcut("$Desktop\GOLDEN_SNIPER.lnk")
    $Shortcut.TargetPath = "$dest\run_golden_sniper.bat"
    $Shortcut.WorkingDirectory = "$dest"
    $Shortcut.IconLocation = "$dest\run_golden_sniper.bat,0"
    $Shortcut.Save()
} catch {}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  [EXITO] CME QUANT BOT ACTUALIZADO SATISFACTORIAMENTE!" -ForegroundColor Green
Write-Host "  Ruta Suite: $dest" -ForegroundColor Green
Write-Host "  Acceso directo 'GOLDEN_SNIPER' creado en tu Escritorio" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""
