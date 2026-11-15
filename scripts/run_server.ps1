# 启动 CCGS 后端开发服务器（默认 127.0.0.1:8770）
# 用法：powershell -ExecutionPolicy Bypass -File scripts/run_server.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONUTF8 = '1'
if (-not $env:CCGS_PORT) { $env:CCGS_PORT = '8770' }
if (-not $env:CCGS_HOST) { $env:CCGS_HOST = '127.0.0.1' }
Write-Host "CCGS backend -> http://$($env:CCGS_HOST):$($env:CCGS_PORT)" -ForegroundColor Cyan
Write-Host "DB: $($env:CCGS_DB_PATH)" -ForegroundColor DarkGray
python -m app.backend.server
