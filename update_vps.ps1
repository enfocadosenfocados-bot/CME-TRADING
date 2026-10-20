# One-Click CME Quant Bot Updater for VPS
$dest = "C:\CME_Quant_Bot"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$zipB64 = (Invoke-RestMethod -Uri "https://dpaste.org/su0Uk/raw").Trim()
$bytes = [Convert]::FromBase64String($zipB64)
$tempZip = "$env:TEMP\cme_bot_bundle.zip"
[System.IO.File]::WriteAllBytes($tempZip, $bytes)
Expand-Archive -Path $tempZip -DestinationPath $dest -Force
Remove-Item $tempZip -Force -ErrorAction SilentlyContinue
Write-Host "[SUCCESS] All files updated in $dest!" -ForegroundColor Green
