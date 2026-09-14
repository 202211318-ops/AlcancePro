$root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $root "backend")
& .\.venv\Scripts\python -m uvicorn app.main:app --port 8008
