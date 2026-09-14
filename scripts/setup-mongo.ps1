$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$zip = Join-Path $root "tools\mongodb.zip"
$dest = Join-Path $root "tools"
if (-not (Test-Path $zip)) { throw "Falta $zip" }
Write-Host "Extrayendo MongoDB portable..."
Expand-Archive -Path $zip -DestinationPath $dest -Force
Get-ChildItem $dest -Directory | Where-Object { $_.Name -like "mongodb-*" } | Select-Object -First 1 | ForEach-Object { Write-Host "Listo en $($_.FullName)" }
