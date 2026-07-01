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
        .\tools\dev.ps1 build-fast corona_engine
        .\tools\dev.ps1 rebuild corona_engine
        .\tools\dev.ps1 build corona_engine -Configuration Release
        .\tools\dev.ps1 update
        .\tools\dev.ps1 clean
#>
[CmdletBinding()]
Param(
    [Parameter(Position = 0)]
    [ValidateSet("status", "install", "configure", "build", "build-fast", "rebuild", "update", "clean")]
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

function Remove-RepoPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $target = Join-Path $RepoRoot $RelativePath
    if (-not (Test-Path -LiteralPath $target)) {
        Write-Host "[INFO] Not found: $RelativePath"
        return
    }

    $resolvedTarget = (Resolve-Path -LiteralPath $target).Path
    $resolvedRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
    $rootPrefix = $resolvedRoot.TrimEnd("\") + "\"
    if (($resolvedTarget -eq $resolvedRoot) -or (-not $resolvedTarget.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase))) {
        throw "Refusing to remove path outside repository root: $resolvedTarget"
    }

    Write-Host "[INFO] Removing $resolvedTarget"
    Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
}

function Invoke-CleanBuildTree {
    Remove-RepoPath -RelativePath "build"
    Remove-RepoPath -RelativePath "install"
}

function Invoke-CleanProject {
    Write-Host "[INFO] Removing ignored local build/cache files"
    Invoke-NativeCommand -FilePath "git" -Arguments @("clean", "-fdX")
}

function Get-ConanBuildDir {
    return (Join-Path $RepoRoot "build\conan")
}

function Convert-ToComparablePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    return $Path.Replace("\", "/").TrimEnd("/").ToLowerInvariant()
}

function Get-CMakeCacheValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CacheFile,

        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    foreach ($line in (Get-Content -LiteralPath $CacheFile)) {
        if ($line -match "^$([regex]::Escape($Name)):[^=]*=(.*)$") {
            return $Matches[1]
        }
    }

    return $null
}

function Assert-CMakeCacheMatchesRepo {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CacheFile
    )

    $sourceDir = Get-CMakeCacheValue -CacheFile $CacheFile -Name "CMAKE_HOME_DIRECTORY"
    if ($sourceDir) {
        $expectedSource = Convert-ToComparablePath -Path $RepoRoot
        $actualSource = Convert-ToComparablePath -Path $sourceDir
        if ($actualSource -ne $expectedSource) {
            throw "CMake cache belongs to '$sourceDir', not '$RepoRoot'. Run '.\tools\dev.ps1 rebuild $($Target[0])'."
        }
    }

    $cacheDir = Get-CMakeCacheValue -CacheFile $CacheFile -Name "CMAKE_CACHEFILE_DIR"
    if ($cacheDir) {
        $expectedCacheDir = Convert-ToComparablePath -Path (Get-ConanBuildDir)
        $actualCacheDir = Convert-ToComparablePath -Path $cacheDir
        if ($actualCacheDir -ne $expectedCacheDir) {
            throw "CMake cache directory is '$cacheDir', not '$(Get-ConanBuildDir)'. Run '.\tools\dev.ps1 rebuild $($Target[0])'."
        }
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

function Assert-NoEditableReference {
    param([Parameter(Mandatory = $true)][string]$Reference)

    $editableList = & conan editable list
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    if ($editableList -match "^$([regex]::Escape($Reference))\b") {
        throw "Editable Conan reference '$Reference' is not allowed for CoronaEngine builds. Remove it with 'conan editable remove $Reference' or consume a package from cache/remote."
    }
}

function Export-LocalRecipes {
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

function Get-ConanInstallOptions {
    $targetValues = @($Target)
    $options = @()

    foreach ($targetValue in $targetValues) {
        $lowerTarget = $targetValue.ToLowerInvariant()
        if ($lowerTarget.Contains("test")) {
            $options += "&:with_tests=True"
            break
        }
    }

    foreach ($targetValue in $targetValues) {
        $lowerTarget = $targetValue.ToLowerInvariant()
        if ($lowerTarget.Contains("vision") -or $lowerTarget.Contains("oidn")) {
            $options += "&:with_vision=True"
            break
        }
    }

    foreach ($targetValue in $targetValues) {
        $lowerTarget = $targetValue.ToLowerInvariant()
        if ($lowerTarget.Contains("oidn")) {
            $options += "&:with_oidn=True"
            break
        }
    }

    return $options
}

function Invoke-ConanInstall {
    param([bool]$Update = $false)

    Assert-NoEditableReference -Reference "horizon/0.5.0"
    if ($Update) {
        Clear-UpdatablePackageCache
    }
    Export-LocalRecipes

    $profile = Get-ConanProfile
    $installOptions = @(Get-ConanInstallOptions)
    $installArguments = @(
        "install",
        ".",
        "-pr:a", $profile,
        "-pr:b", $profile
    )
    foreach ($option in $installOptions) {
        $installArguments += @("-o", $option)
    }
    $installArguments += "--build=missing"

    if ($Update) {
        $installArguments += "--update"
    }

    Invoke-NativeCommand -FilePath "conan" -Arguments $installArguments
}

function Invoke-CMakeConfigure {
    Import-ConanBuildEnvironment
    Invoke-NativeCommand -FilePath "cmake" -Arguments @("--preset", "conan-default")
}

function Invoke-CMakeBuild {
    $buildDir = Get-ConanBuildDir
    $cacheFile = Join-Path $buildDir "CMakeCache.txt"
    if (-not (Test-Path -LiteralPath $cacheFile)) {
        throw "CMake cache was not found. Run '.\tools\dev.ps1 configure' or '.\tools\dev.ps1 build' first."
    }
    Assert-CMakeCacheMatchesRepo -CacheFile $cacheFile

    Invoke-NativeCommand -FilePath "cmake" -Arguments @("--build", $buildDir, "--config", $Configuration, "--target", $Target[0])
}

Push-Location -LiteralPath $RepoRoot
try {
    if ($Command -ne "clean") {
        Initialize-ToolShims
    }

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
            Invoke-CMakeConfigure
        }
        "build" {
            Invoke-ConanInstall
            Invoke-CMakeConfigure
            Invoke-CMakeBuild
        }
        "build-fast" {
            Import-ConanBuildEnvironment
            Invoke-CMakeBuild
        }
        "rebuild" {
            Invoke-CleanBuildTree
            Invoke-ConanInstall
            Invoke-CMakeConfigure
            Invoke-CMakeBuild
        }
        "update" {
            Invoke-ConanInstall -Update $true
            Invoke-CMakeConfigure
        }
        "clean" {
            Invoke-CleanProject
        }
    }
}
finally {
    Pop-Location
}
