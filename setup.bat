@echo off
title offGIT - One-Click Automated Installer
echo ===================================================
echo             offGIT Automated Setup
echo ===================================================
echo.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Installation encountered an issue. Please review the output above.
)
echo.
echo Press any key to exit...
pause >nul
