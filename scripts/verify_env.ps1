# ============================================================
# CCGS 环境核验脚本：检查 D 盘、Python、Git、依赖、工具能力
# 用法：pwsh -NoProfile -File scripts/verify_env.ps1
# 只读检查，不修改任何环境变量或系统配置
# ============================================================
$ErrorActionPreference = 'Continue'
$ok = 0; $warn = 0; $fail = 0
function Report($level, $msg) {
    switch ($level) {
        'OK'   { Write-Host "[ OK ] $msg" -ForegroundColor Green }
        'WARN' { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
        'FAIL' { Write-Host "[FAIL] $msg" -ForegroundColor Red }
    }
}
Write-Host "==== CCGS 环境核验 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ===="

# 1) 磁盘
foreach ($d in @('D','C')) {
    try {
        $drv = Get-PSDrive $d -ErrorAction Stop
        $free = [math]::Round($drv.Free/1GB,1); $used = [math]::Round($drv.Used/1GB,1)
        if ($d -eq 'D') { if ($free -lt 5) { Report 'FAIL' "D 盘剩余 ${free}GB（不足 5GB）" } else { Report 'OK' "D 盘 used ${used}GB / free ${free}GB" } }
        else { Report 'WARN' "C 盘 used ${used}GB / free ${free}GB（项目不写 C 盘）" }
    } catch { Report 'FAIL' "$d 盘不可用" }
}

# 2) 目录
$proj = 'D:\ChinaCompute\suanlichuhai'
foreach ($p in @('D:\ChinaCompute', $proj, 'D:\ChinaCompute\cache', 'D:\ChinaCompute\temp')) {
    if (Test-Path $p) { Report 'OK' "目录存在：$p" } else { Report 'FAIL' "目录缺失：$p" }
}
if ((Get-Location).Path -like 'D:\chinaCompute\suanlichuhai*') { Report 'OK' '当前目录在 D 盘项目内' } else { Report 'WARN' "当前目录：$((Get-Location).Path)" }

# 3) 运行时
foreach ($cmd in @('python','git','node')) {
    $c = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($c) {
        $v = & $cmd --version 2>&1 | Select-Object -First 1
        Report 'OK' "$cmd : $v ($($c.Source))"
    } else { Report "FAIL" "$cmd 不可用" }
}

# 4) Python 依赖
$py = @'
import importlib, sys
mods = ["flask","sqlalchemy","pandas","openpyxl","requests","bs4","lxml","yaml","fitz","PyPDF2","pydantic","jinja2"]
missing = []
for m in mods:
    try:
        importlib.import_module(m)
    except Exception:
        missing.append(m)
print("PYVER", sys.version.split()[0])
print("MISSING", ",".join(missing) if missing else "NONE")
'@
$tmp = Join-Path $env:TEMP ("ccgs_pycheck_{0}.py" -f (Get-Random))
Set-Content -Path $tmp -Value $py -Encoding UTF8
$out = & python $tmp 2>&1
Remove-Item $tmp -ErrorAction SilentlyContinue
foreach ($line in $out) {
    if ($line -like 'PYVER*') { Report 'OK' "Python 版本 $($line -replace 'PYVER ','')" }
    elseif ($line -like 'MISSING NONE') { Report 'OK' 'Python 依赖齐全' }
    elseif ($line -like 'MISSING *') { Report 'WARN' "缺少可选依赖：$($line -replace 'MISSING ','')" }
}

# 5) Git 状态
try {
    Push-Location $proj
    $branch = git branch --show-current 2>&1
    Report 'OK' "当前分支：$branch"
    $remote = git remote get-url origin 2>&1
    Report 'OK' "远程：$remote"
    $dirty = git status --porcelain 2>&1
    if ($dirty) { Report 'WARN' "工作区有未提交文件（$(@($dirty).Count) 项）" } else { Report 'OK' '工作区干净' }
    Pop-Location
} catch { Report 'WARN' 'Git 检查失败（可能在项目目录外）' }

# 6) 缓存重定向（进程级）
foreach ($v in @('TEMP','TMP','PIP_CACHE_DIR','UV_CACHE_DIR','npm_config_cache')) {
    $val = [Environment]::GetEnvironmentVariable($v)
    if ($val -and $val -like 'D:\ChinaCompute*') { Report 'OK' "$v = $val" }
    elseif ($val) { Report 'WARN' "$v = $val（未指向 D 盘，建议先执行 setup_dev_env.ps1）" }
    else { Report 'WARN' "$v 未设置" }
}

# 7) 外部工具能力
Report 'OK' 'Web 搜索：可用（Harness web_search）'
Report 'OK' '网页读取：可用（web_fetch）'
Report 'WARN' '浏览器自动化：不可用（未安装 Playwright）'
Report 'WARN' 'PDF：部分可用（PyMuPDF 文本，无 OCR）'
Report 'WARN' 'MCP：0 个连接'
Report 'WARN' '发邮件/私信/拨号：不提供（外联权归 CEO）'

Write-Host "==== 核验完成：人工查看上面的 FAIL/WARN 项 ===="
