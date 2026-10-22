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

# Detectar interprete de Python disponible en el sistema (sin forzar 3.13)
$pyCmd = $null
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $pyCmd = "python"
} elseif (Get-Command "py" -ErrorAction SilentlyContinue) {
    $test = & py -3 --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $pyCmd = "py -3"
    } else {
        $pyCmd = "py"
    }
}

if ($pyCmd) {
    Write-Host "Instalando y verificando librerias con: $pyCmd..." -ForegroundColor Cyan
    & cmd /c "$pyCmd -m pip install -r `"$dest\requirements.txt`""
} else {
    Write-Host "[AVISO] Python no esta en el PATH. Ejecute install.bat si necesita configurar Python." -ForegroundColor Yellow
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
