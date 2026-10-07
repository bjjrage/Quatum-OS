@echo off
setlocal
cd /d "%~dp0"
if not exist "scripts\os_launcher.py" (
  echo ERROR: no encuentro scripts\os_launcher.py en "%CD%".
  exit /b 1
)
where uv >nul 2>nul
if errorlevel 1 (
  py -3 "scripts\os_launcher.py" start %*
) else (
  uv run --project "%CD%" python "scripts\os_launcher.py" start %*
)
exit /b %errorlevel%
