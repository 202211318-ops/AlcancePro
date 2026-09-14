$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not $root) { $root = Get-Location }
$mongoRoot = Get-ChildItem -Path (Join-Path $root "tools") -Directory | Where-Object { $_.Name -like "mongodb-*" } | Select-Object -First 1
if (-not $mongoRoot) {
  throw "No se encontró MongoDB extraído en tools/. Ejecute scripts\setup-mongo.ps1"
}
$dataDir = Join-Path $root "mongo\data"
$logDir = Join-Path $root "mongo\log"
New-Item -ItemType Directory -Force -Path $dataDir, $logDir | Out-Null
$mongod = Join-Path $mongoRoot.FullName "bin\mongod.exe"
Write-Host "Iniciando MongoDB en mongodb://127.0.0.1:27017 (dbpath $dataDir)"
& $mongod --dbpath $dataDir --port 27017 --bind_ip 127.0.0.1 --logpath (Join-Path $logDir "mongod.log")
