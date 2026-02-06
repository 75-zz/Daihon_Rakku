@echo off
chcp 65001 > nul
cd /d "%~dp0"

set PYTHON_PATH=C:\Users\k75mi\AppData\Local\Programs\Python\Python312\pythonw.exe

if not exist "%PYTHON_PATH%" (
    set PYTHON_PATH=C:\Users\k75mi\AppData\Local\Programs\Python\Python312\python.exe
)

start "" "%PYTHON_PATH%" gui.py
