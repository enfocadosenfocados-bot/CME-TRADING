import os
import zipfile
import io
import base64
import urllib.request
import urllib.parse

files_to_pack = [
    'master_institutional_bot.py',
    'strategy_trinity.py',
    'strategy_pair_trading.py',
    'strategy_cot_squeeze.py',
    'strategy_institutional_hedges.py',
    'run_master_vps.bat',
    'run_advanced_hedges.bat'
]

buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
    for fname in files_to_pack:
        if os.path.exists(fname):
            z.write(fname, arcname=fname)
            print('Packed:', fname)

zip_bytes = buf.getvalue()
b64_str = base64.b64encode(zip_bytes).decode('ascii')

setup_code = f"""import base64, io, zipfile, os
data = base64.b64decode('{b64_str}')
dest = r'C:\\CME_Quant_Bot'
os.makedirs(dest, exist_ok=True)
with zipfile.ZipFile(io.BytesIO(data)) as z:
    z.extractall(dest)
print('SUCCESS: All files extracted to', dest)
"""

with open('setup_bot.py', 'w', encoding='utf-8') as f:
    f.write(setup_code)
print('setup_bot.py generated successfully.')

# Upload raw b64 zip to dpaste
payload = urllib.parse.urlencode({'content': b64_str, 'format': 'raw', 'expiry_days': 14}).encode('utf-8')
req = urllib.request.Request('https://dpaste.org/api/', data=payload)
dpaste_url = urllib.request.urlopen(req).read().decode().strip().replace('"', '')
if not dpaste_url.endswith('/raw'):
    dpaste_url = dpaste_url + '/raw'
print('DPASTE_BUNDLE_URL:', dpaste_url)

# PowerShell script to update VPS
ps1_script = f"""# One-Click CME Quant Bot Updater for VPS
$dest = "C:\\CME_Quant_Bot"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
$zipB64 = (Invoke-RestMethod -Uri "{dpaste_url}").Trim()
$bytes = [Convert]::FromBase64String($zipB64)
$tempZip = "$env:TEMP\\cme_bot_bundle.zip"
[System.IO.File]::WriteAllBytes($tempZip, $bytes)
Expand-Archive -Path $tempZip -DestinationPath $dest -Force
Remove-Item $tempZip -Force -ErrorAction SilentlyContinue
Write-Host "[SUCCESS] All files updated in $dest!" -ForegroundColor Green
"""

with open('update_vps.ps1', 'w', encoding='utf-8') as f:
    f.write(ps1_script)
print('update_vps.ps1 generated.')

payload_ps1 = urllib.parse.urlencode({'content': ps1_script, 'format': 'raw', 'expiry_days': 14}).encode('utf-8')
req_ps1 = urllib.request.Request('https://dpaste.org/api/', data=payload_ps1)
dpaste_ps1 = urllib.request.urlopen(req_ps1).read().decode().strip().replace('"', '')
print('ONE_LINE_PS1_URL:', dpaste_ps1)
