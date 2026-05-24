param(
    [Parameter(Mandatory = $true)]
    [string]$FilePath,
    [string[]]$ArgumentList = @(),
    [int]$TimeoutSec = 600,
    [string]$WorkingDirectory = "",
    [string]$StdoutLog = "",
    [string]$StderrLog = ""
)

$ErrorActionPreference = "Stop"

function Stop-ProcessTree {
    param([int]$ProcessId)
    if ($ProcessId -le 0) {
        return
    }
    $taskkill = Start-Process -FilePath "taskkill.exe" `
        -ArgumentList "/PID", $ProcessId, "/T", "/F" `
        -NoNewWindow `
        -PassThru `
        -Wait
    if ($taskkill.ExitCode -ne 0) {
        Write-Warning "taskkill exited with code $($taskkill.ExitCode) for PID $ProcessId"
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$tmpDir = Join-Path $repoRoot ".agent-os\tmp"
if (!(Test-Path -LiteralPath $tmpDir)) {
    New-Item -ItemType Directory -Path $tmpDir | Out-Null
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
if ([string]::IsNullOrWhiteSpace($WorkingDirectory)) {
    $WorkingDirectory = $repoRoot
}
if ([string]::IsNullOrWhiteSpace($StdoutLog)) {
    $StdoutLog = Join-Path $tmpDir "run-with-timeout-$stamp.out.log"
}
if ([string]::IsNullOrWhiteSpace($StderrLog)) {
    $StderrLog = Join-Path $tmpDir "run-with-timeout-$stamp.err.log"
}

$process = Start-Process -FilePath $FilePath `
    -ArgumentList $ArgumentList `
    -WorkingDirectory $WorkingDirectory `
    -RedirectStandardOutput $StdoutLog `
    -RedirectStandardError $StderrLog `
    -PassThru

$finished = $process.WaitForExit($TimeoutSec * 1000)
if (!$finished) {
    Stop-ProcessTree -ProcessId $process.Id
    Write-Output "status=timeout"
    Write-Output "pid=$($process.Id)"
    Write-Output "timeout_sec=$TimeoutSec"
    Write-Output "stdout=$StdoutLog"
    Write-Output "stderr=$StderrLog"
    exit 124
}

$process.Refresh()
$exitCode = if ($null -eq $process.ExitCode) { 0 } else { [int]$process.ExitCode }

Write-Output "status=completed"
Write-Output "pid=$($process.Id)"
Write-Output "exit_code=$exitCode"
Write-Output "stdout=$StdoutLog"
Write-Output "stderr=$StderrLog"
exit $exitCode
