# ============================================================
# 中国算力出海 · 开发环境初始化（D 盘优先，不改全局环境变量）
# 用法：
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/setup_dev_env.ps1
#   . .\scripts\setup_dev_env.ps1        # 在当前会话生效
# 说明：
#   - 只影响当前进程，不写系统/用户级环境变量。
#   - 项目、缓存、临时文件、构建产物统一放 D:\ChinaCompute。
#   - C 盘仅保留 Harness/VSCode/Git 等程序自身安装，不写项目文件。
# ============================================================
$ErrorActionPreference = 'Stop'

$Root   = 'D:\ChinaCompute'
$Proj   = Join-Path $Root 'suanlichuhai'
$Cache  = Join-Path $Root 'cache'
$Temp   = Join-Path $Root 'temp'

foreach ($p in @($Root, $Proj, $Cache, $Temp,
                 (Join-Path $Cache 'pip'), (Join-Path $Cache 'uv'),
                 (Join-Path $Cache 'npm'), (Join-Path $Cache 'playwright'),
                 (Join-Path $Proj 'private'), (Join-Path $Proj 'data\private'),
                 (Join-Path $Proj 'data\runtime'), (Join-Path $Proj 'backups'))) {
    if (-not (Test-Path $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null }
}

$env:TEMP            = $Temp
$env:TMP             = $Temp
$env:PIP_CACHE_DIR   = Join-Path $Cache 'pip'
$env:UV_CACHE_DIR    = Join-Path $Cache 'uv'
$env:npm_config_cache = Join-Path $Cache 'npm'
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $Cache 'playwright'

$drive = Get-PSDrive D
Write-Output "== ChinaCompute dev env =="
Write-Output "TEMP              = $env:TEMP"
Write-Output "TMP               = $env:TMP"
Write-Output "PIP_CACHE_DIR     = $env:PIP_CACHE_DIR"
Write-Output "UV_CACHE_DIR      = $env:UV_CACHE_DIR"
Write-Output "npm_config_cache  = $env:npm_config_cache"
Write-Output "PLAYWRIGHT_BROWSERS_PATH = $env:PLAYWRIGHT_BROWSERS_PATH"
Write-Output ("D: free {0:N1} GB / used {1:N1} GB" -f ($drive.Free/1GB), ($drive.Used/1GB))
Write-Output "Project root      = $Proj"
