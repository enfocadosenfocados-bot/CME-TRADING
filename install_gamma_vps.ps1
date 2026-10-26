# Instalador Independiente - GAMMA SNIPER 12 (Carpeta 100% Aislada: C:\Gamma_Sniper_Bot)
# No toca ni modifica C:\CME_Quant_Bot (Golden Sniper / Alpha Champions)
$dest = "C:\Gamma_Sniper_Bot"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$zip = "$env:TEMP\gamma_repo.zip"
$ext = "$env:TEMP\gamma_ext"

Write-Host "Descargando GAMMA SNIPER SUITE desde GitHub..." -ForegroundColor Cyan
Invoke-WebRequest -Uri "https://github.com/enfocadosenfocados-bot/CME-TRADING/archive/refs/heads/main.zip" -OutFile $zip

Write-Host "Instalando archivos en carpeta aislada $dest..." -ForegroundColor Cyan
Expand-Archive -Path $zip -DestinationPath $ext -Force

if (Test-Path "$ext\CME-TRADING-main\GAMMA_SNIPER_SUITE") {
    Copy-Item "$ext\CME-TRADING-main\GAMMA_SNIPER_SUITE\*" -Destination $dest -Recurse -Force
} else {
    Copy-Item "$ext\CME-TRADING-main\gamma_sniper_bot.py" -Destination $dest -Force
    Copy-Item "$ext\CME-TRADING-main\run_gamma_sniper.bat" -Destination $dest -Force
    Copy-Item "$ext\CME-TRADING-main\requirements.txt" -Destination $dest -Force
    Copy-Item "$ext\CME-TRADING-main\gex_cache_*.json" -Destination $dest -Force -ErrorAction SilentlyContinue
}

Remove-Item $zip -Force -ErrorAction SilentlyContinue
Remove-Item $ext -Recurse -Force -ErrorAction SilentlyContinue

# Instalar Obscura Stealth Engine (v0.2.5) en C:\Gamma_Sniper_Bot\obscura_bin
$obsDir = "$dest\obscura_bin"
$obsExe = "$obsDir\obscura.exe"
if (-not (Test-Path $obsExe)) {
    Write-Host "Descargando motor Rust Obscura Stealth (v0.2.5) en $obsDir..." -ForegroundColor Cyan
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

# Verificar Python 3.12 / 3.13 compatible con MetaTrader 5
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
    Write-Host "Verificando librerias de MetaTrader 5 y Gamma Exposure con $pyCmd..." -ForegroundColor Cyan
    & cmd /c "$pyCmd -m pip install --upgrade pip --quiet"
    & cmd /c "$pyCmd -m pip install -r `"$dest\requirements.txt`""
}

# Crear acceso directo aislado en el Escritorio
try {
    $WshShell = New-Object -ComObject WScript.Shell
    $Desktop = [Environment]::GetFolderPath("Desktop")

    $Shortcut3 = $WshShell.CreateShortcut("$Desktop\GAMMA_SNIPER_12.lnk")
    $Shortcut3.TargetPath = "$dest\run_gamma_sniper.bat"
    $Shortcut3.WorkingDirectory = "$dest"
    $Shortcut3.IconLocation = "$dest\run_gamma_sniper.bat,0"
    $Shortcut3.Save()
} catch {}

Write-Host ""
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "  [EXITO] GAMMA SNIPER 12 INSTALADO EN CARPETA 100% INDEPENDIENTE!" -ForegroundColor Green
Write-Host "  Carpeta Gamma Sniper : C:\Gamma_Sniper_Bot" -ForegroundColor Green
Write-Host "  Carpeta Golden/Alpha : C:\CME_Quant_Bot (Intacta y separada)" -ForegroundColor Green
Write-Host "  Acceso Directo       : 'GAMMA_SNIPER_12' en tu Escritorio" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green
