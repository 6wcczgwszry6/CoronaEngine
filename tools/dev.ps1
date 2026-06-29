<#
    dev.ps1
    -------
    Unified developer entry point for common CoronaEngine workflows.

    Usage:
        .\tools\dev.ps1 status
        .\tools\dev.ps1 install
        .\tools\dev.ps1 configure
        .\tools\dev.ps1 build
        .\tools\dev.ps1 build CoronaEngine
        .\tools\dev.ps1 build corona_engine -Configuration Release
        .\tools\dev.ps1 update
#>
[CmdletBinding()]
Param(
    [Parameter(Position = 0)]
    [ValidateSet("status", "install", "configure", "build", "update")]
    [string]$Command = "status",

    [Parameter()]
    [ValidateSet("Debug", "Release", "RelWithDebInfo", "MinSizeRel")]
    [string]$Configuration = "Debug",

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [ValidateNotNullOrEmpty()]
    [string[]]$Target = @("corona_engine")
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

function Initialize-ToolShims {
    $shimRoot = Join-Path $RepoRoot "build\conan\tool-shims"
    New-Item -ItemType Directory -Force -Path $shimRoot | Out-Null

    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        $python = Get-Command python3.14 -ErrorAction SilentlyContinue
        if (-not $python) {
            $python = Get-Command python3 -ErrorAction SilentlyContinue
        }
        if ($python) {
            $pythonPath = $python.Source.Replace('"', '""')
            $shimPath = Join-Path $shimRoot "python.cmd"
            Set-Content -LiteralPath $shimPath -Encoding ASCII -Value @(
                "@echo off",
                "`"$pythonPath`" %*"
            )
        }
    }

    $env:PATH = "$shimRoot;$env:PATH"
}

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,

        [string[]]$Arguments = @()
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

function Get-MsvcBuildPreset {
    switch ($Configuration) {
        "Debug" { return "conan-debug" }
        "Release" { return "conan-release" }
        "RelWithDebInfo" { return "conan-relwithdebinfo" }
        "MinSizeRel" { return "conan-minsizerel" }
    }
}

function Import-BatchEnvironment {
    param([Parameter(Mandatory = $true)][string]$BatchFile)

    if (-not (Test-Path -LiteralPath $BatchFile)) {
        throw "Environment batch file was not found: $BatchFile"
    }

    $escapedBatchFile = $BatchFile.Replace('"', '\"')
    $environment = & cmd.exe /d /s /c "`"call `"$escapedBatchFile`" >nul && set`""
    foreach ($line in $environment) {
        $separator = $line.IndexOf("=")
        if ($separator -gt 0) {
            $name = $line.Substring(0, $separator)
            $value = $line.Substring($separator + 1)
            Set-Item -Path "Env:$name" -Value $value
        }
    }
}

function Import-ConanBuildEnvironment {
    $buildEnv = Join-Path $RepoRoot "build\conan\generators\conanbuild.bat"
    Import-BatchEnvironment -BatchFile $buildEnv
}

function Get-ConanProfile {
    switch ($Configuration) {
        "Debug" { return (Join-Path $RepoRoot "conan\profiles\windows-msvc-debug") }
        "Release" { return (Join-Path $RepoRoot "conan\profiles\windows-msvc-release") }
        "RelWithDebInfo" { return (Join-Path $RepoRoot "conan\profiles\windows-msvc-relwithdebinfo") }
        "MinSizeRel" { return (Join-Path $RepoRoot "conan\profiles\windows-msvc-minsizerel") }
    }
}

function Export-LocalRecipes {
    $editableList = & conan editable list
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    if ($editableList -match "^horizon/0\.5\.0\b") {
        Invoke-NativeCommand -FilePath "conan" -Arguments @("editable", "remove", "-r", "horizon/0.5.0")
    }

    $recipes = @(
        "conan\recipes\ktm",
        "conan\recipes\pfr",
        "conan\recipes\slang",
        "conan\recipes\vulkan-memory-allocator",
        "conan\recipes\astc-encoder",
        "conan\recipes\cef-binary",
        "conan\recipes\ffmpeg",
        "conan\recipes\horizon"
    )

    foreach ($recipe in $recipes) {
        Invoke-NativeCommand -FilePath "conan" -Arguments @("export", $recipe)
    }
}

function Clear-UpdatablePackageCache {
    $refs = @(
        "horizon/0.5.0"
    )

    foreach ($ref in $refs) {
        Invoke-NativeCommand -FilePath "conan" -Arguments @("remove", $ref, "-c")
    }
}

function Invoke-ConanInstall {
    param([bool]$Update = $false)

    if ($Update) {
        Clear-UpdatablePackageCache
    }

    Export-LocalRecipes

    $profile = Get-ConanProfile
    $installArguments = @(
        "install",
        ".",
        "-pr:a", $profile,
        "-pr:b", $profile,
        "--build=missing"
    )

    if ($Update) {
        $installArguments += "--update"
    }

    Invoke-NativeCommand -FilePath "conan" -Arguments $installArguments
}

Push-Location -LiteralPath $RepoRoot
try {
    Initialize-ToolShims

    switch ($Command) {
        "status" {
            Invoke-NativeCommand -FilePath "git" -Arguments @("status", "--short", "--branch")
            Invoke-NativeCommand -FilePath "conan" -Arguments @("--version")
            Invoke-NativeCommand -FilePath "cmake" -Arguments @("--list-presets")
        }
        "install" {
            Invoke-ConanInstall
        }
        "configure" {
            Invoke-ConanInstall
            Import-ConanBuildEnvironment
            Invoke-NativeCommand -FilePath "cmake" -Arguments @("--preset", "conan-default")
        }
        "build" {
            Invoke-ConanInstall
            Import-ConanBuildEnvironment
            Invoke-NativeCommand -FilePath "cmake" -Arguments @("--preset", "conan-default")
            Invoke-NativeCommand -FilePath "cmake" -Arguments @("--build", "--preset", (Get-MsvcBuildPreset), "--target", $Target[0])
        }
        "update" {
            Invoke-ConanInstall -Update $true
            Import-ConanBuildEnvironment
            Invoke-NativeCommand -FilePath "cmake" -Arguments @("--preset", "conan-default")
        }
    }
}
finally {
    Pop-Location
}
