@echo off
REM Quick launch script for Drone GCS

echo Starting Drone Ground Control Station...
echo.

REM Activate virtual environment
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo ERROR: Virtual environment not found
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Run application
python main.py

REM Keep window open if error occurs
if errorlevel 1 (
    echo.
    echo Application exited with error
    pause
)
