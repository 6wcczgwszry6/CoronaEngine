param(
    [string]$SourceDir = "D:\yzy\code\cpp\Vision",
    [string]$BuildDir = "D:\yzy\code\cpp\Vision\cmake-build-codex-msvc2",
    [int]$TimeoutSec = 900
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$tmpDir = Join-Path $repoRoot ".agent-os\tmp"
if (!(Test-Path -LiteralPath $tmpDir)) {
    New-Item -ItemType Directory -Path $tmpDir | Out-Null
}

if (!(Test-Path -LiteralPath $BuildDir)) {
    New-Item -ItemType Directory -Path $BuildDir | Out-Null
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$stdoutLog = Join-Path $tmpDir "cmake-config-$stamp.out.log"
$stderrLog = Join-Path $tmpDir "cmake-config-$stamp.err.log"
$exitFile = Join-Path $tmpDir "cmake-config-$stamp.exit.txt"
$stateFile = Join-Path $tmpDir "cmake-config-$stamp.state.json"
$watchdogOutLog = Join-Path $tmpDir "cmake-config-$stamp.watchdog.out.log"
$watchdogErrLog = Join-Path $tmpDir "cmake-config-$stamp.watchdog.err.log"

$vcvars = "C:\Program Files\Microsoft Visual Studio\18\Insiders\VC\Auxiliary\Build\vcvars64.bat"
$cmake = "D:\Program Files (x86)\CLion 2025.3.1.1\bin\cmake\win\x64\bin\cmake.exe"
$cl = "C:/Program Files/Microsoft Visual Studio/18/Insiders/VC/Tools/MSVC/14.50.35615/bin/Hostx64/x64/cl.exe"
$python = "C:/Users/Vice/AppData/Local/Python/pythoncore-3.14-64/python.exe"

$command = "set VSCMD_DEBUG=0 && call `"$vcvars`" >nul && `"$cmake`" -S `"$SourceDir`" -B `"$BuildDir`" -G Ninja -DCMAKE_BUILD_TYPE=Debug -DCMAKE_C_COMPILER=`"$cl`" -DCMAKE_CXX_COMPILER=`"$cl`" -DPython_EXECUTABLE=`"$python`" 1> `"$stdoutLog`" 2> `"$stderrLog`" & set CONFIG_EXIT=!errorlevel! & echo !CONFIG_EXIT! > `"$exitFile`""
$process = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/v:on", "/d", "/c", $command `
    -WorkingDirectory $repoRoot `
    -PassThru

$state = [ordered]@{
    pid = $process.Id
    step = "cmake-config"
    source_dir = $SourceDir
    build_dir = $BuildDir
    timeout_sec = $TimeoutSec
    start_time_utc = (Get-Date).ToUniversalTime().ToString("o")
    stdout_log = $stdoutLog
    stderr_log = $stderrLog
    exit_file = $exitFile
}
$state | ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding UTF8

$watcher = Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "watch_async_step.ps1"), "-StateFile", $stateFile `
    -WindowStyle Hidden `
    -PassThru

$state.watchdog_pid = $watcher.Id
$state.watchdog_stdout_log = $watchdogOutLog
$state.watchdog_stderr_log = $watchdogErrLog
$state | ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding UTF8

Write-Output "state_file=$stateFile"
Write-Output "pid=$($process.Id)"
Write-Output "watchdog_pid=$($watcher.Id)"
Write-Output "stdout=$stdoutLog"
Write-Output "stderr=$stderrLog"
Write-Output "exit_file=$exitFile"
