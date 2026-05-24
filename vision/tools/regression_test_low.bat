@echo off
REM Run low-precision regression test: fast render and loose comparison against golden
REM Double-click to run, no arguments needed

setlocal
set OPENCV_IO_ENABLE_OPENEXR=1
set PYTHON=python
set SCRIPT_DIR=%~dp0dev_verify
set BUILD_DIR=%~dp0..\cmake-build-release
set SPP=200
set THRESHOLD=0.04
set OUTPUT_NAME=test_image_low.exr

echo ============================================
echo   Low-Precision Regression Test (SPP=%SPP%, DS8 RMSE threshold=%THRESHOLD%)
echo ============================================
echo.

echo --- Step 1: Render low-precision test images ---
"%PYTHON%" "%SCRIPT_DIR%\regression_render.py" --build-dir "%BUILD_DIR%" --spp %SPP% --output-name %OUTPUT_NAME%
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Rendering failed.
    pause
    exit /b 1
)

echo.
echo --- Step 2: Compare against golden images ---
"%PYTHON%" "%SCRIPT_DIR%\regression_compare.py" --test %OUTPUT_NAME% --threshold %THRESHOLD%

echo.
if %ERRORLEVEL% EQU 0 (
    echo [DONE] Low-precision regression test passed.
) else (
    echo [FAIL] Low-precision regression test failed. Check report_regression.md
)
echo.
pause