# ============================================================
# CCGS 全量测试入口
# 用法：pwsh -NoProfile -File scripts/run_tests.ps1
# 说明：使用标准库 unittest（环境无 pytest），临时 DB 不污染 data/runtime
# ============================================================
$ErrorActionPreference = 'Continue'
. (Join-Path $PSScriptRoot 'setup_dev_env.ps1') | Out-Null
$proj = 'D:\ChinaCompute\suanlichuhai'
Push-Location $proj
try {
    Write-Host '==== CCGS unittest ====' -ForegroundColor Cyan
    $env:CCGS_ENV = 'test'
    python -m unittest discover -s tests -v 2>&1 | Tee-Object -Variable out
    $code = $LASTEXITCODE
    Write-Host ''
    if ($code -eq 0) { Write-Host '[ OK ] 测试全部通过' -ForegroundColor Green }
    else { Write-Host "[FAIL] 测试失败（exit $code）" -ForegroundColor Red }
    exit $code
} finally { Pop-Location }
