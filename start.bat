@echo off
setlocal enabledelayedexpansion
title Fin-Eye Dev Startup

set "ROOT=C:\Users\ahmty\fin-eye"
set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"

echo.
echo  ==========================================================
echo      Fin-Eye  --  Dev Environment Startup
echo  ==========================================================
echo.

:: ── Step 1: Docker (Postgres + Redis) ──────────────────────────────────────
echo [1/6] Starting Docker containers (wiping Redis volume for clean auth)...
cd /d "%ROOT%"
docker compose down >nul 2>&1
docker volume rm fin-eye_redis_data >nul 2>&1
docker compose up -d
if %errorlevel% neq 0 (
    echo  ERROR: Docker failed. Is Docker Desktop running?
    pause & exit /b 1
)
echo  OK -- Containers started.
echo.

:: ── Step 2: Wait for Postgres ──────────────────────────────────────────────
echo [2/6] Waiting for Postgres to be ready...
set /a tries=0
:wait_pg
set /a tries+=1
docker exec fin-eye-db pg_isready -U postgres -d fin_eye >nul 2>&1
if %errorlevel% equ 0 goto pg_ready
if %tries% geq 20 (
    echo  ERROR: Postgres did not become ready in time.
    pause & exit /b 1
)
timeout /t 2 /nobreak >nul
goto wait_pg
:pg_ready
echo  OK -- Postgres ready after %tries% check(s).
echo.

:: ── Step 3: Alembic migrations ─────────────────────────────────────────────
echo [3/6] Running database migrations...
cd /d "%BACKEND%"
alembic upgrade head
if %errorlevel% neq 0 (
    echo  ERROR: Alembic migration failed.
    pause & exit /b 1
)
echo  OK -- Migrations applied.
echo.

:: ── Step 4: Create admin user ──────────────────────────────────────────────
echo [4/6] Ensuring admin user exists...
python create_admin.py
echo  OK -- Admin check done.
echo.

:: ── Step 5: Start backend ──────────────────────────────────────────────────
echo [5/6] Starting backend (uvicorn) in new window...
start "Fin-Eye Backend" cmd /k "cd /d %BACKEND% && uvicorn app.main:app --reload --port 8000"
echo  OK -- Backend window opened.
echo.

:: ── Step 6: Start frontend ─────────────────────────────────────────────────
echo [6/6] Starting frontend (Next.js) in new window...
start "Fin-Eye Frontend" cmd /k "cd /d %FRONTEND% && npm run dev"
echo  OK -- Frontend window opened.
echo.

echo  ==========================================================
echo    Fin-Eye is starting up!
echo.
echo    Frontend :  http://localhost:3000
echo    Backend  :  http://localhost:8000
echo    API Docs :  http://localhost:8000/docs
echo    Admin    :  admin@yagmurterminal.com  /  admin
echo  ==========================================================
echo.
echo  Press any key to close this launcher.
pause >nul
