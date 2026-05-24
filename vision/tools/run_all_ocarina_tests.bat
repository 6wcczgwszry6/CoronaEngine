@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

for %%I in ("%SCRIPT_DIR%\..") do set "ROOT_DIR=%%~fI"
set "OCARINA_TEST_CMAKE=%ROOT_DIR%\src\ocarina\src\tests\CMakeLists.txt"
set "BIN_DIR="
set "FAILED=0"
set "TOTAL=0"
set "FAILED_TESTS="

if /I "%~1"=="-h" goto :usage
if /I "%~1"=="--help" goto :usage

if not "%~1"=="" (
    set "BIN_DIR=%~f1"
) else (
    call :pick_default_bin_dir
)

if not defined BIN_DIR (
    echo [ERROR] No Ocarina test bin directory found.
    echo [ERROR] Checked: cmake-build-release\bin, cmake-build-relwithdebinfo\bin, cmake-build-debug\bin
    goto :exit_failure
)

if not exist "%BIN_DIR%" (
    echo [ERROR] Bin directory not found: %BIN_DIR%
    goto :exit_failure
)

if not exist "%OCARINA_TEST_CMAKE%" (
    echo [ERROR] Ocarina test CMake file not found: %OCARINA_TEST_CMAKE%
    goto :exit_failure
)

pushd "%BIN_DIR%" >nul
if errorlevel 1 (
    echo [ERROR] Failed to enter bin directory: %BIN_DIR%
    goto :exit_failure
)

echo [INFO] Running Ocarina tests from %BIN_DIR%
call :run_tests_from_cmake "%OCARINA_TEST_CMAKE%"

popd >nul

echo.
echo [INFO] Executed %TOTAL% Ocarina test^(s^).
if "%FAILED%"=="0" (
    echo [INFO] All Ocarina tests passed.
    exit /b 0
)

echo [ERROR] %FAILED% test^(s^) failed.
echo [ERROR] Failed tests:%FAILED_TESTS%
goto :exit_failure

:pick_default_bin_dir
if exist "%ROOT_DIR%\cmake-build-release\bin" (
    set "BIN_DIR=%ROOT_DIR%\cmake-build-release\bin"
    exit /b 0
)
if exist "%ROOT_DIR%\cmake-build-relwithdebinfo\bin" (
    set "BIN_DIR=%ROOT_DIR%\cmake-build-relwithdebinfo\bin"
    exit /b 0
)
if exist "%ROOT_DIR%\cmake-build-debug\bin" (
    set "BIN_DIR=%ROOT_DIR%\cmake-build-debug\bin"
    exit /b 0
)
exit /b 0

:run_tests_from_cmake
for /f "usebackq delims=" %%L in (`findstr /R /C:"^[ ]*ocarina_add_test(" "%~1"`) do (
    set "LINE=%%L"
    call :run_test_from_line
)
exit /b 0

:run_test_from_line
set "REST=!LINE:*ocarina_add_test(=!"
set "RAW_NAME="
set "RAW_CATEGORY="
for /f "tokens=1,2,3 delims= " %%A in ("!REST!") do (
    set "RAW_NAME=%%~A"
    set "RAW_CATEGORY=%%~C"
)

if not defined RAW_NAME exit /b 0
if not defined RAW_CATEGORY exit /b 0

set "TEST_NAME=!RAW_NAME:)=!"
set "CATEGORY=!RAW_CATEGORY:)=!"
set "ACTUAL_TARGET=!TEST_NAME!"

if /I "!TEST_NAME:~0,5!"=="test-" (
    set "ACTUAL_TARGET=test-!CATEGORY!-!TEST_NAME:~5!"
)

call :run_test "!ACTUAL_TARGET!.exe"
set "RAW_NAME="
set "RAW_CATEGORY="
set "TEST_NAME="
set "CATEGORY="
set "ACTUAL_TARGET="
exit /b 0

:run_test
set /a TOTAL+=1
echo.
echo [TEST %TOTAL%] %~1

if not exist ".\%~1" (
    echo [FAIL] Missing executable: %~1
    set /a FAILED+=1
    set "FAILED_TESTS=!FAILED_TESTS! %~1"
    exit /b 0
)

".\%~1"
set "TEST_EXIT_CODE=%ERRORLEVEL%"
if not "%TEST_EXIT_CODE%"=="0" (
    echo [FAIL] %~1 exited with code %TEST_EXIT_CODE%.
    set /a FAILED+=1
    set "FAILED_TESTS=!FAILED_TESTS! %~1"
    exit /b 0
)

echo [PASS] %~1
exit /b 0

:usage
echo Usage:
echo   run_all_ocarina_tests.bat [bin_dir]
echo.
echo Examples:
echo   run_all_ocarina_tests.bat
echo   run_all_ocarina_tests.bat d:\work\corona\Vision\cmake-build-debug\bin
echo.
echo Run all Ocarina tests without building anything.
echo If no bin_dir is provided, the script tries Release, RelWithDebInfo, then Debug.
exit /b 0

:exit_failure
echo.
echo [HINT] There are failing tests or script errors. Press any key to close this window.
pause >nul
exit /b 1