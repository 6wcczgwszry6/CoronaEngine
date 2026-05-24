@echo off
REM Full development verification: build + unit tests + format check + regression
REM Double-click to run, no arguments needed

setlocal
set OPENCV_IO_ENABLE_OPENEXR=1
set PYTHON=python
set SCRIPT_DIR=%~dp0dev_verify
set BUILD_DIR=%~dp0..\cmake-build-release
set TARGET=vision-gui
set CONFIG=Release
set SPP=200
set THRESHOLD=0.01

set PASS_COUNT=0
set FAIL_COUNT=0
set TOTAL=4

echo ############################################################
echo   Vision Dev Verify - Full Pipeline
echo   Config=%CONFIG%  Target=%TARGET%  SPP=%SPP%
echo ############################################################
echo.

REM === Stage 1: Build ===
echo ============================================
echo   [1/4] Build (%CONFIG%, target=%TARGET%)
echo ============================================
pushd "%BUILD_DIR%"
for /f "usebackq tokens=*" %%i in (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VSINSTALL=%%i"
cmd /c "\"%VSINSTALL%\VC\Auxiliary\Build\vcvarsall.bat\" x64 >nul 2>&1 && ninja -j8 %TARGET%"
if %ERRORLEVEL% EQU 0 (
    echo   [PASS] Build
    set /a PASS_COUNT+=1
) else (
    echo   [FAIL] Build
    set /a FAIL_COUNT+=1
)
popd
echo.

REM === Stage 2: Unit Tests ===
echo ============================================
echo   [2/4] Unit Tests
echo ============================================
"%PYTHON%" "%SCRIPT_DIR%\run_tests.py" --build-dir "%BUILD_DIR%" --tests test-param_schema test-material-energy --ensure-targets test-param_schema test-material-energy
if %ERRORLEVEL% EQU 0 (
    echo   [PASS] Unit Tests
    set /a PASS_COUNT+=1
) else (
    echo   [FAIL] Unit Tests
    set /a FAIL_COUNT+=1
)
echo.

REM === Stage 3: Format Check ===
echo ============================================
echo   [3/4] Format Check
echo ============================================
"%PYTHON%" "%SCRIPT_DIR%\format_check.py"
if %ERRORLEVEL% EQU 0 (
    echo   [PASS] Format Check
    set /a PASS_COUNT+=1
) else (
    echo   [FAIL] Format Check
    set /a FAIL_COUNT+=1
)
echo.

REM === Stage 4: Regression Test ===
echo ============================================
echo   [4/4] Regression Test
echo ============================================
echo --- Ensure golden images ---
"%PYTHON%" "%SCRIPT_DIR%\generate_golden.py" --build-dir "%BUILD_DIR%" --spp %SPP%
echo --- Render test images ---
"%PYTHON%" "%SCRIPT_DIR%\regression_render.py" --build-dir "%BUILD_DIR%" --spp %SPP% --output-name test_image.exr
echo --- Compare ---
"%PYTHON%" "%SCRIPT_DIR%\regression_compare.py" --threshold %THRESHOLD%
if %ERRORLEVEL% EQU 0 (
    echo   [PASS] Regression Test
    set /a PASS_COUNT+=1
) else (
    echo   [FAIL] Regression Test
    set /a FAIL_COUNT+=1
)
echo.

REM === Summary ===
echo ############################################################
echo   SUMMARY: %PASS_COUNT%/%TOTAL% passed, %FAIL_COUNT% failed
echo ############################################################
echo.
echo Reports saved in tools\dev_verify\:
echo   - report_unit_tests.md
echo   - report_format.md
echo   - report_golden.md
echo   - report_render_test_image.md
echo   - report_regression.md
echo.

if %FAIL_COUNT% GTR 0 (
    echo [RESULT] Some stages FAILED.
) else (
    echo [RESULT] All stages PASSED.
)
echo.
pause
