@echo off
REM Run unit tests
REM Double-click to run, no arguments needed

setlocal
set PYTHON=python
set SCRIPT_DIR=%~dp0dev_verify
set BUILD_DIR=%~dp0..\cmake-build-release

echo ============================================
echo   Unit Tests
echo ============================================
echo.

"%PYTHON%" "%SCRIPT_DIR%\run_tests.py" --build-dir "%BUILD_DIR%" --tests test-param_schema test-material-energy --ensure-targets test-param_schema test-material-energy

echo.
if %ERRORLEVEL% EQU 0 (
    echo [DONE] All unit tests passed.
) else (
    echo [FAIL] Some tests failed. Check report_unit_tests.md
)
echo.
pause
