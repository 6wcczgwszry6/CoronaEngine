@echo off
REM Check code formatting with clang-format
REM Double-click to run, no arguments needed

setlocal
set PYTHON=python
set SCRIPT_DIR=%~dp0dev_verify

echo ============================================
echo   Format Check (clang-format)
echo ============================================
echo.

"%PYTHON%" "%SCRIPT_DIR%\format_check.py"

echo.
if %ERRORLEVEL% EQU 0 (
    echo [DONE] All files properly formatted.
) else (
    echo [FAIL] Format violations found. Check report_format.md
)
echo.
pause
