@echo off
echo.
echo ====================================================
echo    Personal Agentic Factory - Windows Setup
echo ====================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    pause
    exit /b 1
)
echo [OK] Python found

:: Install deps
echo [PAF] Installing dependencies...
pip install -r requirements.txt --quiet
echo [OK] Dependencies installed

:: Copy .env
if not exist .env (
    copy .env.example .env
    echo [WARN] .env created. Edit it and add your API keys before running.
) else (
    echo [OK] .env already exists
)

:: Create dirs
mkdir factory_jobs 2>nul
mkdir factory_state 2>nul
mkdir factory_logs 2>nul
echo [OK] Output directories created

echo.
echo ====================================================
echo  Setup done. Next steps:
echo.
echo  1. Edit .env with your API keys
echo  2. Run:  python main.py
echo.
echo  Or test directly:
echo    python main.py build "build a BTC price tracker"
echo ====================================================
echo.
pause
