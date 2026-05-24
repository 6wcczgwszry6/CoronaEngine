@echo off
setlocal EnableDelayedExpansion

if "%~1"=="" (
    echo Usage: tmp_build_all.bat ^<build-dir^> [log-file]
    exit /b 2
)

set "BUILD_DIR=%~1"
set "LOG_FILE=%~2"

if not "%LOG_FILE%"=="" (
    call :run > "%LOG_FILE%" 2>&1
    set "RET=!ERRORLEVEL!"
    >> "%LOG_FILE%" echo EXITCODE:!RET!
    exit /b !RET!
)

call :run
exit /b %ERRORLEVEL%

:run
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x64 >nul 2>&1
if errorlevel 1 exit /b %errorlevel%

cd /d "%BUILD_DIR%"
if errorlevel 1 exit /b %errorlevel%

ninja -j8
exit /b %errorlevel%