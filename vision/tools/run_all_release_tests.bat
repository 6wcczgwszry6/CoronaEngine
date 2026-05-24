@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

for %%I in ("%SCRIPT_DIR%\..") do set "ROOT_DIR=%%~fI"
set "BIN_DIR=%ROOT_DIR%\cmake-build-release\bin"
set "VISION_TEST_CMAKE=%ROOT_DIR%\src\tests\CMakeLists.txt"
set "OCARINA_TEST_CMAKE=%ROOT_DIR%\src\ocarina\src\tests\CMakeLists.txt"
set "FAILED=0"
set "TOTAL=0"
set "FAILED_TESTS="

if /I "%~1"=="-h" goto :usage
if /I "%~1"=="--help" goto :usage

if not exist "%BIN_DIR%" (
    echo [ERROR] Release bin directory not found: %BIN_DIR%
    exit /b 1
)

if not exist "%VISION_TEST_CMAKE%" (
    echo [ERROR] Vision test CMake file not found: %VISION_TEST_CMAKE%
    exit /b 1
)

if not exist "%OCARINA_TEST_CMAKE%" (
    echo [ERROR] Ocarina test CMake file not found: %OCARINA_TEST_CMAKE%
    exit /b 1
)

pushd "%BIN_DIR%" >nul
if errorlevel 1 (
    echo [ERROR] Failed to enter Release bin directory.
    exit /b 1
)

echo [INFO] Running Ocarina Release tests...
call :run_tests_from_cmake "%OCARINA_TEST_CMAKE%" ocarina_add_test

echo [INFO] Running Vision Release tests...
call :run_tests_from_cmake "%VISION_TEST_CMAKE%" vision_add_test
call :run_tests_from_cmake "%VISION_TEST_CMAKE%" vision_add_simple_test

popd >nul

echo.
echo [INFO] Executed %TOTAL% Release tests.
if "%FAILED%"=="0" (
    echo [INFO] All tests passed.
    exit /b 0
)

echo [ERROR] %FAILED% test^(s^) failed.
echo [ERROR] Failed tests:%FAILED_TESTS%
exit /b 1

:run_tests_from_cmake
for /f "usebackq tokens=1,2 delims=( " %%A in (`findstr /R /C:"^[ ]*%~2(" "%~1"`) do (
    call :run_test "%%~B.exe"
)
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
echo   run_all_release_tests.bat
echo.
echo Run all Ocarina and Vision Release tests from cmake-build-release\bin.
exit /b 0