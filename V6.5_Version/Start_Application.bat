@echo off
REM BMIoT Configuration Generator Launcher
REM Double-click this file to start the application

echo.
echo ========================================
echo  BMIoT Configuration Generator v6.6
echo ========================================
echo.
echo Starting application...
echo.

python modbus_tkinter_app_v6.6_complete.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo  ERROR: Could not start application
    echo ========================================
    echo.
    echo Possible reasons:
    echo  1. Python is not installed
    echo  2. Python is not in PATH
    echo.
    echo Please install Python 3.7+ from:
    echo  https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH"
    echo during installation.
    echo.
    pause
) else (
    echo.
    echo Application closed.
    pause
)
