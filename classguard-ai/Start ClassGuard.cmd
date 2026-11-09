@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-local.ps1"
if errorlevel 1 (
    echo.
    echo ClassGuard could not start. Read the message above.
    pause
    exit /b 1
)
