@echo off
REM ══════════════════════════════════════════════════════════════════════════
REM  Fin-Eye — BUG-013 Fix Script
REM  Run from: C:\Users\ahmty\fin-eye
REM
REM  This script:
REM   1. Removes backend/.env from git tracking (keeps file on disk)
REM   2. Removes tracked .joblib/.pkl model artifacts from git tracking
REM   3. Removes the scratch scheduler_header.py file
REM   4. Commits the untracking changes
REM
REM  ⚠️  AFTER RUNNING THIS: rotate all secrets in backend/.env
REM      (JWT_SECRET, REDIS_PASSWORD, all API keys)
REM ══════════════════════════════════════════════════════════════════════════

echo [1/5] Removing backend\.env from git tracking...
git rm --cached backend/.env 2>nul
if errorlevel 1 (
    echo      Already untracked or not found — skipping
) else (
    echo      Done.
)

echo.
echo [2/5] Removing tracked .joblib model artifacts from git tracking...
git rm --cached backend/data/models/AAPL_1d_winner.joblib 2>nul
git rm --cached backend/data/models/AAPL_1h_winner.joblib 2>nul
git rm --cached backend/data/models/AAPL_1wk_winner.joblib 2>nul
git rm --cached backend/data/models/model_registry.jsonl.bak 2>nul
echo      Done.

echo.
echo [3/5] Removing scratch file scheduler_header.py...
git rm --cached backend/app/services/scheduler_header.py 2>nul
del /f backend\app\services\scheduler_header.py 2>nul
echo      Done.

echo.
echo [4/5] Checking model_store directory...
if exist model_store\ (
    dir /b model_store\ 2>nul | findstr /r "." >nul
    if errorlevel 1 (
        echo      model_store\ is empty — removing...
        rmdir /s /q model_store\
        echo      Done.
    ) else (
        echo      model_store\ has contents — skipping auto-delete, review manually.
        dir /b model_store\
    )
) else (
    echo      model_store\ does not exist — nothing to do.
)

echo.
echo [5/5] Committing untracking changes...
git add -A
git commit -m "chore: untrack backend/.env, model artifacts, and scratch files (BUG-013)"

echo.
echo ══════════════════════════════════════════════════════════════════════════
echo  DONE. 
echo.
echo  ⚠️  IMPORTANT: backend\.env was tracked — secrets may be in git history.
echo  Rotate these NOW:
echo    - JWT_SECRET
echo    - REDIS_PASSWORD
echo    - FINNHUB_API_KEY
echo    - OPENAI_API_KEY
echo    - STRIPE_SECRET_KEY
echo    - Any other keys present in backend\.env
echo.
echo  To fully purge from git history (optional, destructive):
echo    git filter-branch --force --index-filter ^
echo      "git rm --cached --ignore-unmatch backend/.env" ^
echo      --prune-empty --tag-name-filter cat -- --all
echo ══════════════════════════════════════════════════════════════════════════
pause
