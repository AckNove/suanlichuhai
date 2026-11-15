# Run the CCGS unittest suite (see docs/07_ai_system/RUNBOOK.md).
# unittest writes progress to stderr; Start-Process + redirect avoids Windows
# PowerShell 5.1 treating that stderr as a terminating native-command error.
# Keep this file ASCII-only so Windows PowerShell 5.1 parses it without a BOM.

$repo = Split-Path -Parent $PSScriptRoot
. (Join-Path $repo 'scripts\setup_dev_env.ps1')

$outLog = Join-Path $env:TEMP 'ccgs_unittest_stdout.log'
$errLog = Join-Path $env:TEMP 'ccgs_unittest_stderr.log'

Push-Location $repo
try {
    Write-Output '==== CCGS unittest ===='
    $proc = Start-Process -FilePath 'python' `
        -ArgumentList @('-m', 'unittest', 'discover', '-s', 'tests', '-v') `
        -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $outLog -RedirectStandardError $errLog
    foreach ($f in @($errLog, $outLog)) {
        if (Test-Path $f) {
            Get-Content $f -Encoding UTF8 | ForEach-Object { Write-Output $_ }
        }
    }
    Write-Output ('==== unittest exit code: {0} ====' -f $proc.ExitCode)
    exit $proc.ExitCode
}
finally {
    Pop-Location
}
