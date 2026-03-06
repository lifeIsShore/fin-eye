@echo off
cd /d Y:\programing\projects\fin-eye\backend
echo ============================================
echo  Fin-Eye — Batch ML Training Script
echo  Training 9 tickers x 5 timeframes = 45 runs
echo  Estimated time: 3-6 hours total
echo  Tip: Run this overnight
echo ============================================
echo.

echo [1/9] Training AAPL...
python scripts/run_technical_training.py --symbol AAPL --start 2018-01-01T00:00:00 --end 2025-01-01T00:00:00 --timeframe all

echo [2/9] Training MSFT...
python scripts/run_technical_training.py --symbol MSFT --start 2018-01-01T00:00:00 --end 2025-01-01T00:00:00 --timeframe all

echo [3/9] Training GOOGL...
python scripts/run_technical_training.py --symbol GOOGL --start 2018-01-01T00:00:00 --end 2025-01-01T00:00:00 --timeframe all

echo [4/9] Training AMZN...
python scripts/run_technical_training.py --symbol AMZN --start 2018-01-01T00:00:00 --end 2025-01-01T00:00:00 --timeframe all

echo [5/9] Training TSLA...
python scripts/run_technical_training.py --symbol TSLA --start 2018-01-01T00:00:00 --end 2025-01-01T00:00:00 --timeframe all

echo [6/9] Training NVDA...
python scripts/run_technical_training.py --symbol NVDA --start 2018-01-01T00:00:00 --end 2025-01-01T00:00:00 --timeframe all

echo [7/9] Training SPY...
python scripts/run_technical_training.py --symbol SPY --start 2018-01-01T00:00:00 --end 2025-01-01T00:00:00 --timeframe all

echo [8/9] Training QQQ...
python scripts/run_technical_training.py --symbol QQQ --start 2018-01-01T00:00:00 --end 2025-01-01T00:00:00 --timeframe all

echo [9/9] Training META...
python scripts/run_technical_training.py --symbol META --start 2018-01-01T00:00:00 --end 2025-01-01T00:00:00 --timeframe all

echo.
echo ============================================
echo  All training complete!
echo  Models saved in: backend\model_store\artifacts\
echo ============================================
pause
