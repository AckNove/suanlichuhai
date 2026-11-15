# ============================================================
# CCGS 提交前敏感信息扫描
# 用法：pwsh -NoProfile -File scripts/sensitive_scan.ps1 [-Strict]
#   -Strict：发现邮箱/电话等疑似联系方式也返回失败（默认为 WARN）
# 扫描范围：Git 跟踪文件 + 未忽略的未跟踪文件（即将提交的内容）
# 退出码：0 通过；1 发现高危项（密钥、私钥、数据库文件）
# ============================================================
param([switch]$Strict)
$ErrorActionPreference = 'Stop'
$proj = 'D:\ChinaCompute\suanlichuhai'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
Push-Location $proj
try {
    $files = git -c core.quotepath=false ls-files --cached --others --exclude-standard 2>$null
} finally { }
if (-not $files) { Write-Host '[WARN] 无文件可扫描'; Pop-Location; exit 0 }

$self = 'scripts/sensitive_scan.ps1'
$highPatterns = @(
    @{ name = '私钥';        regex = '-----BEGIN [A-Z ]*PRIVATE KEY-----' },
    @{ name = 'GitHub Token'; regex = ('gh' + '[pousr]_[A-Za-z0-9]{20,}') },
    @{ name = 'GitHub PAT';   regex = ('github' + '_pat_[A-Za-z0-9_]{20,}') },
    @{ name = 'AWS Key';      regex = ('AK' + 'IA[0-9A-Z]{16}') },
    @{ name = 'OpenAI Key';   regex = ('sk' + '-[A-Za-z0-9]{20,}') },
    @{ name = 'Anthropic Key';regex = ('sk' + '-ant-[A-Za-z0-9\-]{20,}') },
    @{ name = 'Slack Token';  regex = ('xox' + '[bpas]-[A-Za-z0-9\-]{10,}') },
    @{ name = 'Bearer Token'; regex = ('Bearer ' + '[A-Za-z0-9\-\._~\+/]{30,}') }
)
$medPatterns = @(
    @{ name = '邮箱地址';    regex = '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' },
    @{ name = '中国手机号';  regex = '(?<!\d)1[3-9]\d{9}(?!\d)' },
    @{ name = '疑似密码赋值'; regex = '(?i)(password|passwd|pwd|secret|api[_-]?key|access[_-]?key)\s*[:=]\s*["''][^"'']{6,}' }
)
$placeholderDomains = @('example.com','example.org','yourcompany','domain.com','placeholder','xxx.com','test.com','sample.com','localhost')
$binaryExt = @('.db','.sqlite','.sqlite3','.zip','.7z','.rar','.pdf','.xlsx','.xls','.docx','.pptx','.jpg','.jpeg','.png','.pem','.key','.p12','.pfx')

$highHits = @(); $medHits = @(); $binHits = @(); $binLegacy = @()
foreach ($f in $files) {
    if ($f -eq $self) { continue }
    $ext = [IO.Path]::GetExtension($f).ToLower()
    if ($binaryExt -contains $ext) {
        # 历史交接快照中的既有二进制（2026-11-13 之前由前任提交，不得删除历史文件）→ 仅提示
        if ($f -like 'docs/handover-20261113/*' -or $f -like 'downloads/*') { $binLegacy += $f; continue }
        $binHits += $f; continue
    }
    if (-not (Test-Path -LiteralPath $f -PathType Leaf)) { continue }
    try { $lines = Get-Content -LiteralPath $f -Encoding UTF8 -ErrorAction Stop } catch { continue }
    $ln = 0
    foreach ($line in $lines) {
        $ln++
        if ($line.Length -gt 4000) { continue }
        foreach ($p in $highPatterns) {
            if ($line -match $p.regex) { $highHits += "${f}:$ln [$($p.name)] $($line.Trim().Substring(0,[Math]::Min(80,$line.Trim().Length)))" }
        }
        foreach ($p in $medPatterns) {
            if ($line -match $p.regex) {
                $matched = $Matches[0]
                $isPlaceholder = $false
                foreach ($d in $placeholderDomains) { if ($matched.ToLower().Contains($d)) { $isPlaceholder = $true } }
                if ($p.name -eq '中国手机号') {
                    if ($line -match '占位|placeholder|示例|XXXX|xxxx|\*\*\*\*') { $isPlaceholder = $true }
                }
                if (-not $isPlaceholder) { $medHits += "${f}:$ln [$($p.name)] $($line.Trim().Substring(0,[Math]::Min(80,$line.Trim().Length)))" }
            }
        }
    }
}

Write-Host "==== CCGS 敏感信息扫描 ====" -ForegroundColor Cyan
Write-Host "扫描文件数：$(@($files).Count)"
Write-Host "高危命中：$($highHits.Count)  中危命中：$($medHits.Count)  二进制/数据文件：$($binHits.Count)  历史既有二进制（豁免）：$($binLegacy.Count)"
if ($binLegacy.Count -gt 0) { Write-Host "[INFO] 历史交接快照既有二进制，保持原样不新增：" -ForegroundColor DarkGray; $binLegacy | ForEach-Object { Write-Host "  - $_" } }
if ($binHits.Count -gt 0) {
    Write-Host "[FAIL] 以下二进制/数据文件不应提交（检查 .gitignore）：" -ForegroundColor Red
    $binHits | Select-Object -First 20 | ForEach-Object { Write-Host "  - $_" }
}
if ($highHits.Count -gt 0) {
    Write-Host "[FAIL] 疑似密钥/凭据：" -ForegroundColor Red
    $highHits | Select-Object -First 30 | ForEach-Object { Write-Host "  - $_" }
}
if ($medHits.Count -gt 0) {
    Write-Host "[WARN] 疑似个人联系方式/密码（请确认是否占位符）：" -ForegroundColor Yellow
    $medHits | Select-Object -First 30 | ForEach-Object { Write-Host "  - $_" }
}
if ($highHits.Count -eq 0 -and $binHits.Count -eq 0 -and (-not $Strict -or $medHits.Count -eq 0)) {
    Write-Host "[ OK ] 扫描通过" -ForegroundColor Green
    Pop-Location; exit 0
}
Write-Host "[FAIL] 扫描未通过，请处理后再提交" -ForegroundColor Red
Pop-Location; exit 1
