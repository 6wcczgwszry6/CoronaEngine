param(
    [Parameter(Mandatory = $true)]
    [string]$StateFile
)

$ErrorActionPreference = "Stop"

function Stop-ProcessTree {
    param([int]$ProcessId)
    if ($ProcessId -le 0) {
        return
    }
    Start-Process -FilePath "taskkill.exe" `
        -ArgumentList "/PID", $ProcessId, "/T", "/F" `
        -NoNewWindow `
        -PassThru `
        -Wait | Out-Null
}

$state = Get-Content -LiteralPath $StateFile -Raw | ConvertFrom-Json
$startUtc = [DateTime]::Parse($state.start_time_utc).ToUniversalTime()
$elapsed = ((Get-Date).ToUniversalTime() - $startUtc).TotalSeconds
$process = Get-Process -Id $state.pid -ErrorAction SilentlyContinue
$timeoutMarker = "$StateFile.timeout.json"

if (Test-Path -LiteralPath $timeoutMarker) {
    $marker = Get-Content -LiteralPath $timeoutMarker -Raw | ConvertFrom-Json
    Write-Output "status=timeout"
    Write-Output "pid=$($marker.pid)"
    Write-Output "elapsed_sec=$($marker.elapsed_sec)"
    Write-Output "stdout=$($marker.stdout)"
    Write-Output "stderr=$($marker.stderr)"
    exit 124
}

if ($process -and $elapsed -gt [double]$state.timeout_sec) {
    Stop-ProcessTree -ProcessId $state.pid
    Write-Output "status=timeout"
    Write-Output "pid=$($state.pid)"
    Write-Output "elapsed_sec=$([int]$elapsed)"
    Write-Output "stdout=$($state.stdout_log)"
    Write-Output "stderr=$($state.stderr_log)"
    exit 124
}

if ($process) {
    Write-Output "status=running"
    Write-Output "pid=$($state.pid)"
    Write-Output "elapsed_sec=$([int]$elapsed)"
    Write-Output "stdout=$($state.stdout_log)"
    Write-Output "stderr=$($state.stderr_log)"
    exit 0
}

$exitCode = -1
if (Test-Path -LiteralPath $state.exit_file) {
    $exitCode = [int](Get-Content -LiteralPath $state.exit_file -Raw).Trim()
}

Write-Output "status=completed"
Write-Output "exit_code=$exitCode"
Write-Output "stdout=$($state.stdout_log)"
Write-Output "stderr=$($state.stderr_log)"
exit $exitCode
