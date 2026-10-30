@echo off
cd /d "%~dp0"
".venv-api\Scripts\python.exe" -m apps.run_local stop
