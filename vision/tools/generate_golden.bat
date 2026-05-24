@echo off
REM Generate golden reference images for all test scenes
REM Double-click to run, no arguments needed

setlocal
set OPENCV_IO_ENABLE_OPENEXR=1
set PYTHON=python
set SCRIPT_DIR=%~dp0dev_verify
set BUILD_DIR=%~dp0..\cmake-build-release
set SPP=2000

echo ============================================
echo   Generate Golden Images (SPP=%SPP%)
echo ============================================
echo.

"%PYTHON%" "%SCRIPT_DIR%\generate_golden.py" --build-dir "%BUILD_DIR%" --spp %SPP%

echo.
if %ERRORLEVEL% EQU 0 (
    echo [DONE] Golden image generation completed.
) else (
    echo [ERROR] Some scenes failed. Check report_golden.md
)
echo.
pause
