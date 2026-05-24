@echo off
REM Delete all golden_image.exr files from test scenes
REM Only deletes from scene dirs that have vision_scene.json

setlocal
set SCENE_ROOT=%~dp0..\..\CoronaTestScenes\test_vision\render_scene

echo ============================================
echo   Delete Golden Images
echo ============================================
echo.
echo Scene root: %SCENE_ROOT%
echo.

set COUNT=0
for /d %%D in ("%SCENE_ROOT%\*") do (
    if exist "%%D\vision_scene.json" (
        if exist "%%D\golden_image.exr" (
            del /f "%%D\golden_image.exr"
            echo   DELETED  %%~nxD\golden_image.exr
            set /a COUNT+=1
        )
    )
)

echo.
echo Deleted %COUNT% golden_image.exr file(s).
echo.
pause
