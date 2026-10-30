@echo off
cd /d "%~dp0"
if not exist ".venv-api\Scripts\python.exe" (
  echo Run Setup.cmd first. See TEAM-SETUP.md.
  pause
  exit /b 1
)
".venv-api\Scripts\python.exe" -m apps.run_local start %*
if errorlevel 1 (
  echo Startup failed. Inspect work\runtime\launcher logs and TEAM-SETUP.md.
  pause
  exit /b 1
)
start "NyayaSarathi" "http://127.0.0.1:8000/"
