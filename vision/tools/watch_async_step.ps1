param(
    [Parameter(Mandatory = $true)]
    [string]$StateFile,
    [int]$PollSec = 5
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

function Remove-StaleNinjaLock {
    param([string]$ResolvedBuildDir)
    if ([string]::IsNullOrWhiteSpace($ResolvedBuildDir)) {
        return
    }
    $lockPath = Join-Path $ResolvedBuildDir ".ninja_lock"
    if (Test-Path -LiteralPath $lockPath) {
        Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
    }
}

$timeoutMarker = "$StateFile.timeout.json"

while ($true) {
    if (!(Test-Path -LiteralPath $StateFile)) {
        exit 0
    }
    $state = Get-Content -LiteralPath $StateFile -Raw | ConvertFrom-Json
    $process = Get-Process -Id $state.pid -ErrorAction SilentlyContinue
    if (!$process) {
        exit 0
    }

    $startUtc = [DateTime]::Parse($state.start_time_utc).ToUniversalTime()
    $elapsed = ((Get-Date).ToUniversalTime() - $startUtc).TotalSeconds
    if ($elapsed -gt [double]$state.timeout_sec) {
        Stop-ProcessTree -ProcessId $state.pid
        if ($null -ne $state.build_dir) {
            Remove-StaleNinjaLock -ResolvedBuildDir $state.build_dir
        }
        $marker = [ordered]@{
            status = "timeout"
            pid = $state.pid
            elapsed_sec = [int]$elapsed
            timeout_sec = [int]$state.timeout_sec
            stdout = $state.stdout_log
            stderr = $state.stderr_log
            killed_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        }
        $marker | ConvertTo-Json | Set-Content -LiteralPath $timeoutMarker -Encoding UTF8
        exit 124
    }
    Start-Sleep -Seconds $PollSec
}
