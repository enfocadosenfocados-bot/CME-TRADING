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

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  [EXITO] CME QUANT BOT ACTUALIZADO SATISFACTORIAMENTE!" -ForegroundColor Green
Write-Host "  Ruta: $dest" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""
