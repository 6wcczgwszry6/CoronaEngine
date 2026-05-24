@echo off
REM Run regression test: render test images and compare against golden
REM Double-click to run, no arguments needed

setlocal
set OPENCV_IO_ENABLE_OPENEXR=1
set PYTHON=python
set SCRIPT_DIR=%~dp0dev_verify
set BUILD_DIR=%~dp0..\cmake-build-release
set SPP=2000
set THRESHOLD=0.002

echo ============================================
echo   Regression Test (SPP=%SPP%, DS8 RMSE threshold=%THRESHOLD%)
echo ============================================
echo.

echo --- Step 1: Render test images ---
"%PYTHON%" "%SCRIPT_DIR%\regression_render.py" --build-dir "%BUILD_DIR%" --spp %SPP% --output-name test_image.exr
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Rendering failed.
    pause
    exit /b 1
)

echo.
echo --- Step 2: Compare against golden images ---
"%PYTHON%" "%SCRIPT_DIR%\regression_compare.py" --threshold %THRESHOLD%

echo.
if %ERRORLEVEL% EQU 0 (
    echo [DONE] Regression test passed.
) else (
    echo [FAIL] Regression test failed. Check report_regression.md
)
echo.
pause
