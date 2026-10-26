# One-Click CME Quant Bot & Gamma Exposure Sniper Updater from GitHub
# Instala Golden Sniper + Alpha Champions en C:\CME_Quant_Bot
# Instala Gamma Sniper 12 en su propia carpeta independiente C:\Gamma_Sniper_Bot
$dest = "C:\CME_Quant_Bot"
$gammaDest = "C:\Gamma_Sniper_Bot"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
New-Item -ItemType Directory -Force -Path $gammaDest | Out-Null
$zip = "$env:TEMP\cme_repo.zip"
$ext = "$env:TEMP\cme_ext"

Write-Host "Descargando la suite mas reciente desde GitHub..." -ForegroundColor Cyan
Invoke-WebRequest -Uri "https://github.com/enfocadosenfocados-bot/CME-TRADING/archive/refs/heads/main.zip" -OutFile $zip

Write-Host "Descomprimiendo y actualizando Golden/Alpha en $dest y Gamma Sniper en $gammaDest..." -ForegroundColor Cyan
Expand-Archive -Path $zip -DestinationPath $ext -Force
Copy-Item "$ext\CME-TRADING-main\*" -Destination $dest -Recurse -Force

if (Test-Path "$ext\CME-TRADING-main\GAMMA_SNIPER_SUITE") {
    Copy-Item "$ext\CME-TRADING-main\GAMMA_SNIPER_SUITE\*" -Destination $gammaDest -Recurse -Force
} else {
    Copy-Item "$ext\CME-TRADING-main\gamma_sniper_bot.py" -Destination $gammaDest -Force
    Copy-Item "$ext\CME-TRADING-main\run_gamma_sniper.bat" -Destination $gammaDest -Force
    Copy-Item "$ext\CME-TRADING-main\requirements.txt" -Destination $gammaDest -Force
    Copy-Item "$ext\CME-TRADING-main\gex_cache_*.json" -Destination $gammaDest -Force -ErrorAction SilentlyContinue
}

Remove-Item $zip -Force -ErrorAction SilentlyContinue
Remove-Item $ext -Recurse -Force -ErrorAction SilentlyContinue

# Instalar Obscura Stealth Engine (v0.2.5) en $gammaDest\obscura_bin
$obsDir = "$gammaDest\obscura_bin"
$obsExe = "$obsDir\obscura.exe"
if (-not (Test-Path $obsExe)) {
    Write-Host "Descargando motor Rust Obscura Stealth (v0.2.5) para scraping institucional CME..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path $obsDir | Out-Null
    $obsZip = "$env:TEMP\obscura_stealth.zip"
    try {
        Invoke-WebRequest -Uri "https://github.com/h4ckf0r0day/obscura/releases/download/v0.2.5/obscura-x86_64-windows-stealth.zip" -OutFile $obsZip
        Expand-Archive -Path $obsZip -DestinationPath $obsDir -Force
        Remove-Item $obsZip -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] Obscura Stealth instalado en $obsExe" -ForegroundColor Green
    } catch {
        Write-Host "[!] Aviso descargando Obscura: $_ (El bot usara fallback directo CBOE/HTTP)" -ForegroundColor Yellow
    }
} else {
    Write-Host "[OK] Motor Obscura Stealth ya instalado en $obsExe" -ForegroundColor Green
}

# MetaTrader 5 solo es compatible con Python 3.10, 3.11, 3.12 o 3.13
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

if (-not $pyCmd) {
    Write-Host "Instalando Python 3.12 oficial (100% compatible con MetaTrader 5)..." -ForegroundColor Cyan
    & py install 3.12
    $pyCmd = "py -3.12"
}

if ($pyCmd) {
    Write-Host "Instalando dependencias de MetaTrader 5 y Gamma Exposure con $pyCmd..." -ForegroundColor Cyan
    & cmd /c "$pyCmd -m pip install --upgrade pip --quiet"
    & cmd /c "$pyCmd -m pip install -r `"$dest\requirements.txt`""
} else {
    Write-Host "[ERROR] Por favor ejecuta 'py install 3.12' para instalar la version compatible." -ForegroundColor Red
}

# Crear accesos directos en el escritorio apuntando a sus carpetas separadas
try {
    $WshShell = New-Object -ComObject WScript.Shell
    $Desktop = [Environment]::GetFolderPath("Desktop")
    
    $Shortcut1 = $WshShell.CreateShortcut("$Desktop\GOLDEN_SNIPER.lnk")
    $Shortcut1.TargetPath = "$dest\run_golden_sniper.bat"
    $Shortcut1.WorkingDirectory = "$dest"
    $Shortcut1.IconLocation = "$dest\run_golden_sniper.bat,0"
    $Shortcut1.Save()

    $Shortcut2 = $WshShell.CreateShortcut("$Desktop\ALPHA_CHAMPIONS.lnk")
    $Shortcut2.TargetPath = "$dest\run_alpha_champions.bat"
    $Shortcut2.WorkingDirectory = "$dest"
    $Shortcut2.IconLocation = "$dest\run_alpha_champions.bat,0"
    $Shortcut2.Save()

    $Shortcut3 = $WshShell.CreateShortcut("$Desktop\GAMMA_SNIPER_12.lnk")
    $Shortcut3.TargetPath = "$gammaDest\run_gamma_sniper.bat"
    $Shortcut3.WorkingDirectory = "$gammaDest"
    $Shortcut3.IconLocation = "$gammaDest\run_gamma_sniper.bat,0"
    $Shortcut3.Save()
} catch {}

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "  [EXITO] SUITES ACTUALIZADAS EN CARPETAS SEPARADAS EN TU VPS!" -ForegroundColor Green
Write-Host "  Carpeta Golden & Alpha : $dest" -ForegroundColor Green
Write-Host "  Carpeta Gamma Sniper   : $gammaDest" -ForegroundColor Green
Write-Host "  Accesos Directos en tu Escritorio:" -ForegroundColor Green
Write-Host "   1. GOLDEN_SNIPER   -> C:\CME_Quant_Bot (Magic: 880100 - 880600)" -ForegroundColor Green
Write-Host "   2. ALPHA_CHAMPIONS -> C:\CME_Quant_Bot (Magic: 20261024 - 20268803)" -ForegroundColor Green
Write-Host "   3. GAMMA_SNIPER_12 -> C:\Gamma_Sniper_Bot (Magic: 20269901 - 20269912)" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green
