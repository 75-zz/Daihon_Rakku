@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo === FANZA同人 CG集生成ツール ===
echo.

set PYTHON_PATH=C:\Users\k75mi\AppData\Local\Programs\Python\Python312\python.exe

if not exist "%PYTHON_PATH%" (
    echo Error: Pythonが見つかりません
    echo パス: %PYTHON_PATH%
    pause
    exit /b 1
)

echo Pythonを実行中...
"%PYTHON_PATH%" main.py

if %errorlevel% neq 0 (
    echo.
    echo エラーが発生しました (エラーコード: %errorlevel%)
)

pause
