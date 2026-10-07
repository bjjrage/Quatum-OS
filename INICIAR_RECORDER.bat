@echo off
title Quant OS - RECORDER (no cierres esta ventana)
cd /d "%~dp0"

:: Pide permisos de administrador UNA sola vez (para corregir el reloj).
:: Si la ventana elevada tampoco los tiene, sigue igual: nunca reintenta en bucle.
net session >nul 2>&1
if %errorlevel%==0 goto :admin
if /i "%~1"=="elevado" goto :sinadmin
echo Pidiendo permisos de administrador (acepta el aviso de Windows)...
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -ArgumentList 'elevado' -Verb RunAs" >nul 2>&1
if %errorlevel%==0 exit /b
echo No se pudo pedir permisos: sigo sin corregir la hora.
goto :sinadmin

:admin
echo ===================================================
echo  1/2  Corrigiendo la hora de Windows...
echo ===================================================
net start w32time >nul 2>&1
w32tm /resync
goto :arrancar

:sinadmin
echo ===================================================
echo  1/2  Sin permisos de administrador: la hora NO se corrige.
echo       (para corregirla: clic derecho - Ejecutar como administrador)
echo ===================================================

:arrancar
echo.
echo ===================================================
echo  2/2  Arrancando el recorder.
echo  DEJA ESTA VENTANA ABIERTA. Si la cerras, deja de grabar.
echo ===================================================
echo.
uv run python scripts\run_recorder.py

echo.
echo El recorder se detuvo. Si no fue a proposito, cerra esta ventana y volve a abrir el archivo.
pause
