@echo off
cd /d "%~dp0"
py -3.12 -m apps.setup_local %*
if errorlevel 1 (
  echo Setup did not finish. Read the error above and TEAM-SETUP.md.
  pause
  exit /b 1
)
