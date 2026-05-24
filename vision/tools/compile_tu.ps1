param(
    [Parameter(Mandatory = $true)]
    [string]$File,
    [string]$BuildDir = "D:\yzy\code\cpp\Vision\cmake-build-debug-msvc"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$tmpDir = Join-Path $repoRoot ".agent-os\tmp"
if (!(Test-Path -LiteralPath $tmpDir)) {
    New-Item -ItemType Directory -Path $tmpDir | Out-Null
}

$compileDb = Join-Path $BuildDir "compile_commands.json"
$normalized = [IO.Path]::GetFullPath($File).Replace('\', '/')
$entry = Get-Content -LiteralPath $compileDb -Raw | ConvertFrom-Json | Where-Object {
    $_.file -eq $normalized
} | Select-Object -First 1

if ($null -eq $entry) {
    throw "compile_commands entry not found for $normalized"
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$cmdFile = Join-Path $tmpDir "compile-tu-$stamp.cmd"
$vcvars = "C:\Program Files\Microsoft Visual Studio\18\Insiders\VC\Auxiliary\Build\vcvars64.bat"

$lines = @(
    "@echo off",
    "set VSCMD_DEBUG=0",
    "call `"$vcvars`" >nul",
    $entry.command
)
Set-Content -LiteralPath $cmdFile -Value $lines -Encoding ASCII

Push-Location $BuildDir
try {
    & cmd.exe /d /c $cmdFile
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
