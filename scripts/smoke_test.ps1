# ============================================================
# CCGS 冒烟测试：启动后端 -> 请求关键端点 -> 关闭
# 用法：pwsh -NoProfile -File scripts/smoke_test.ps1
# 退出码：0 通过；1 失败
# ============================================================
$ErrorActionPreference = 'Continue'
$proj = 'D:\ChinaCompute\suanlichuhai'
Push-Location $proj
$port = if ($env:CCGS_PORT) { $env:CCGS_PORT } else { '8770' }
$base = "http://127.0.0.1:$port"
$log = Join-Path 'D:\ChinaCompute\temp' 'ccgs_smoke_server.log'
if (-not (Test-Path 'D:\ChinaCompute\temp')) { New-Item -ItemType Directory -Force -Path 'D:\ChinaCompute\temp' | Out-Null }

Write-Host "==== CCGS 冒烟测试 ($base) ====" -ForegroundColor Cyan
$proc = Start-Process -FilePath 'python' -ArgumentList '-m','app.backend.server' `
    -WorkingDirectory $proj -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput $log -RedirectStandardError "$log.err"

$endpoints = @(
    '/api/health',
    '/api/health/db',
    '/api/dashboard',
    '/api/demands?page_size=5',
    '/api/supplies?page_size=5',
    '/api/evidence?page_size=5',
    '/api/approvals/pending',
    '/api/agents',
    '/api/skills',
    '/api/reports/pipeline',
    '/'
)
$fail = 0
try {
    $ready = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        try { $null = Invoke-RestMethod -Uri "$base/api/health" -TimeoutSec 2; $ready = $true; break } catch { }
    }
    if (-not $ready) {
        Write-Host '[FAIL] 后端 15 秒内未就绪，日志：' -ForegroundColor Red
        if (Test-Path $log) { Get-Content $log -Tail 30 }
        if (Test-Path "$log.err") { Get-Content "$log.err" -Tail 30 }
        exit 1
    }
    Write-Host '[ OK ] 后端就绪'
    foreach ($ep in $endpoints) {
        try {
            $r = Invoke-WebRequest -Uri "$base$ep" -TimeoutSec 10 -UseBasicParsing
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 300) { Write-Host ("[ OK ] {0,-28} {1}" -f $ep, $r.StatusCode) -ForegroundColor Green }
            else { Write-Host ("[FAIL] {0,-28} {1}" -f $ep, $r.StatusCode) -ForegroundColor Red; $fail++ }
        } catch {
            Write-Host ("[FAIL] {0,-28} {1}" -f $ep, $_.Exception.Message) -ForegroundColor Red; $fail++
        }
    }
    # 匹配引擎实测（用第一条需求与第一条供给，若无数据则跳过）
    try {
        $dem = Invoke-RestMethod -Uri "$base/api/demands?page_size=1"
        $sup = Invoke-RestMethod -Uri "$base/api/supplies?page_size=1"
        if ($dem.items.Count -gt 0 -and $sup.items.Count -gt 0) {
            $body = @{ demand_id = $dem.items[0].id; supply_ids = @($sup.items[0].id); persist = $false } | ConvertTo-Json
            $m = Invoke-RestMethod -Uri "$base/api/match/run" -Method Post -Body $body -ContentType 'application/json' -TimeoutSec 15
            $score = $m.results[0].total_score
            Write-Host "[ OK ] /api/match/run 总分=$score 建议=$($m.results[0].recommendation)" -ForegroundColor Green
        } else { Write-Host '[WARN] 缺需求或供给数据，跳过匹配实测' -ForegroundColor Yellow }
    } catch {
        Write-Host "[FAIL] /api/match/run $($_.Exception.Message)" -ForegroundColor Red; $fail++
    }
} finally {
    if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
}
Pop-Location
if ($fail -eq 0) { Write-Host '[ OK ] 冒烟测试通过' -ForegroundColor Green; exit 0 }
else { Write-Host "[FAIL] 冒烟测试失败项：$fail" -ForegroundColor Red; exit 1 }
