@echo off
setlocal
echo =========================================================
echo Fin-Eye Manual Dev Script
echo =========================================================

:: Ensure we always operate relative to this bat file's location
cd /d "%~dp0"

echo [1/3] Starting Infrastructure (Docker)...
docker compose up -d db redis

echo [2/3] Launching Backend Server...
start "Fin-Eye Backend" cmd /k "cd /d "%~dp0backend" && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo [3/3] Launching Frontend Application...
start "Fin-Eye Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ---------------------------------------------------------
echo Services are starting!
echo - API: http://localhost:8000/docs
echo - Web: http://localhost:3000
echo ---------------------------------------------------------
echo Leave this window open if you want to see this message,
echo or press any key to exit this launcher.
pause
