# Builds the React UI and assembles .space-build/ — the folder you push to a
# Hugging Face Space. Run it from anywhere:  powershell -File deploy\build-space.ps1
$ErrorActionPreference = 'Stop'

$root = (Resolve-Path "$PSScriptRoot\..").Path
$out  = Join-Path $root '.space-build'

Write-Host '==> Building the React frontend' -ForegroundColor Cyan
Push-Location (Join-Path $root 'frontend')
if (-not (Test-Path 'node_modules')) { npm install }
npm run build
Pop-Location

Write-Host '==> Assembling the Space folder' -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $out | Out-Null
# Wipe everything except the Space's own git history.
Get-ChildItem $out -Force | Where-Object { $_.Name -ne '.git' } |
    Remove-Item -Recurse -Force

Copy-Item (Join-Path $root 'deploy\space\*') $out -Recurse -Force
Copy-Item (Join-Path $root 'backend')       $out -Recurse -Force
Copy-Item (Join-Path $root 'frontend\dist') (Join-Path $out 'web') -Recurse -Force
Copy-Item (Join-Path $root 'LICENSE')       $out -Force

Get-ChildItem (Join-Path $out 'backend') -Recurse -Force -Filter '__pycache__' |
    Remove-Item -Recurse -Force

Write-Host ''
Write-Host "==> Ready: $out" -ForegroundColor Green
Write-Host 'First time only:'
Write-Host "  cd $out"
Write-Host '  git init -b main'
Write-Host '  git remote add origin https://huggingface.co/spaces/<your-hf-username>/reviva'
Write-Host 'Every time:'
Write-Host '  git add -A'
Write-Host '  git commit -m "deploy"'
Write-Host '  git push -u origin main --force   # --force only the FIRST time: the Space'
Write-Host '                                    # was created with its own starter commit.'
Write-Host '  # username = your HF name, password = an HF access token (write)'
