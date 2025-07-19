@echo off
echo ========================================
echo GPU Memory Clear Tool
echo ========================================
echo.

echo Checking NVIDIA drivers...
nvidia-smi --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: NVIDIA drivers not found or nvidia-smi not available
    pause
    exit /b 1
)

echo.
echo ========================================
echo Current GPU Status
echo ========================================
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader,nounits

echo.
echo ========================================
echo Running GPU Processes
echo ========================================
nvidia-smi pmon -c 1

echo.
echo ========================================
echo Attempting to clear GPU memory...
echo ========================================

REM Kill Python processes that might be using GPU
echo Killing Python processes...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1

REM Kill any remaining processes using GPU
echo Killing other GPU processes...
for /f "tokens=2" %%i in ('nvidia-smi pmon -c 1 ^| findstr /v "gpu" ^| findstr /v "pid" ^| findstr /v "type" ^| findstr /v "sm" ^| findstr /v "mem" ^| findstr /v "enc" ^| findstr /v "dec"') do (
    if not "%%i"=="" (
        echo Attempting to kill process %%i...
        taskkill /f /pid %%i >nul 2>&1
    )
)

echo.
echo ========================================
echo GPU Status After Clear
echo ========================================
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader,nounits

echo.
echo ========================================
echo Memory clear operation completed.
echo ========================================
pause 