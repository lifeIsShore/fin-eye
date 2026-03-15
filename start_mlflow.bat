@echo off
:: ─────────────────────────────────────────────────────────────────────────────
:: start_mlflow.bat
:: Starts the local MLflow tracking server for fin-eye.
::
:: FIX 1: Uses SQLite backend instead of filesystem store.
::         Filesystem store is deprecated in MLflow as of Feb 2026.
::         SQLite avoids the deprecation warnings and is faster.
::
:: FIX 2: Passes --workers 1 to avoid OSError [WinError 10022].
::         This error occurs on Python 3.14 on Windows when MLflow tries
::         to share sockets across worker processes — a known incompatibility.
::         Single worker mode is correct for local development use.
::
:: UI opens at: http://localhost:5000
:: Keep this window open while you are training models.
:: Data persists in backend\data\mlflow.db — safe to close and reopen.
:: ─────────────────────────────────────────────────────────────────────────────

echo.
echo  fin-eye MLflow Tracking Server
echo  ─────────────────────────────────────────────────────────────
echo  UI:        http://localhost:5000
echo  DB:        backend\data\mlflow.db  (SQLite)
echo  Artifacts: backend\data\mlartifacts\
echo  ─────────────────────────────────────────────────────────────
echo.

cd /d "%~dp0"

:: Create artifact directory if it doesn't exist
if not exist "backend\data\mlartifacts" mkdir "backend\data\mlartifacts"

:: Start MLflow UI
:: --backend-store-uri  : SQLite database (no deprecation warning, faster than filesystem)
:: --default-artifact-root : where .joblib files are stored
:: --workers 1          : avoids OSError WinError 10022 on Python 3.14 / Windows
:: --host 127.0.0.1     : localhost only (safer default; change to 0.0.0.0 for LAN access)
:: --port 5000          : standard MLflow port
python -m mlflow ui ^
  --backend-store-uri "sqlite:///backend/data/mlflow.db" ^
  --default-artifact-root "backend/data/mlartifacts" ^
  --workers 1 ^
  --host 127.0.0.1 ^
  --port 5000

pause
