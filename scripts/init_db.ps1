# 初始化 CCGS 数据库（幂等建表 + 幂等种子）
# 用法：powershell -ExecutionPolicy Bypass -File scripts/init_db.ps1
#   -NoSeed   只建表，不导入种子数据
param(
    [switch]$NoSeed
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONUTF8 = '1'
if ($NoSeed) { $env:CCGS_SEED = '0' }
Write-Host "CCGS DB: $($env:CCGS_DB_PATH)" -ForegroundColor DarkGray
python -m app.backend.db
if (-not $NoSeed -and $env:CCGS_SEED -ne '0') {
    python -m app.backend.seed
}
Write-Host "完成。启动服务：powershell -File scripts/run_server.ps1" -ForegroundColor Cyan
