@echo off
REM Drone GCS Installation Script for Windows
REM Run this script to set up the application

echo ========================================
echo Drone Human Detection ^& Mission Planner
echo Ground Control Station - Setup
echo ========================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

echo [1/4] Python detected successfully
echo.

REM Create virtual environment
echo [2/4] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)
echo Virtual environment created successfully
echo.

REM Activate virtual environment and install dependencies
echo [3/4] Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed successfully
echo.

REM Check for YOLOv8 model
echo [4/4] Checking for YOLOv8 model...
if exist best.pt (
    echo YOLOv8 model found: best.pt
) else (
    echo WARNING: YOLOv8 model 'best.pt' not found
    echo Please place your trained model in the application directory
    echo Or download a pre-trained model:
    echo   python -c "from ultralytics import YOLO; YOLO('yolov8n.pt').save('best.pt')"
)
echo.

echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo To run the application:
echo   1. Activate virtual environment: venv\Scripts\activate
echo   2. Run: python main.py
echo.
echo Or simply run: run_app.bat
echo.
pause
