@echo off
setlocal
echo =========================================================
echo Fin-Eye Manual Dev Script
echo =========================================================

echo [1/3] Starting Infrastructure (Docker)...
docker compose up -d db redis

echo [2/3] Launching Backend Server...
:: Opens in a new command window
start "Fin-Eye Backend" cmd /k "cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo [3/3] Launching Frontend Application...
:: Opens in a new command window
start "Fin-Eye Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ---------------------------------------------------------
echo Services are starting!
echo - API: http://localhost:8000/docs
echo - Web: http://localhost:3000
echo ---------------------------------------------------------
echo Leave this window open if you want to see this message, 
echo or press any key to exit this launcher.
pause
