@echo off
title Quant OS - RECORDER (no cierres esta ventana)
chcp 65001 >nul

:: Pide permisos de administrador solo (para poder corregir el reloj)
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Pidiendo permisos de administrador, aceptá el aviso de Windows...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

echo ===================================================
echo  1/2  Corrigiendo la hora de Windows...
echo ===================================================
net start w32time >nul 2>&1
w32tm /resync

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
