@echo off
REM Run all scene transformation phases.
REM Usage:
REM   run_all.bat                  -- run all 4 phases
REM   run_all.bat --dry-run        -- preview without writing
REM   run_all.bat --phase 1        -- run only phase 1
REM   run_all.bat --phase 3 --phase 4  -- run phases 3 and 4

cd /d "%~dp0..\.."
python -m tools.scene_transform.run_all %*
