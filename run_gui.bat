@echo off
chcp 65001 > nul
cd /d "%~dp0"

set PYTHON=C:\Users\k75mi\AppData\Local\Programs\Python\Python312\python.exe

echo Starting Daihon Rakku...
"%PYTHON%" gui.py

if errorlevel 1 (
    echo.
    echo === ERROR ===
    pause
)
