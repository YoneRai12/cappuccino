@echo off
echo ========================================
echo NVIDIA-SMI Status Viewer
echo ========================================
echo.

echo Checking NVIDIA drivers...
nvidia-smi --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: NVIDIA drivers not found or nvidia-smi not available
    echo Please install NVIDIA drivers
    pause
    exit /b 1
)

echo.
echo ========================================
echo GPU Status
echo ========================================
nvidia-smi

echo.
echo ========================================
echo GPU Memory Usage
echo ========================================
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv

echo.
echo ========================================
echo Running Processes
echo ========================================
nvidia-smi pmon -c 1

echo.
echo ========================================
echo Press any key to exit...
pause >nul 