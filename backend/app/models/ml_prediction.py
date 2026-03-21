"""
app/models/ml_prediction.py

SQLAlchemy model for the ML prediction database (todos-v5 Phase 5.1).

Every time the ML pipeline generates a signal for a user, one row is stored here.
After the horizon period passes, the outcome_resolver cron fills in the actual
price + direction, enabling live accuracy tracking.

This creates a feedback loop:
  Train → Predict → Store → Resolve → Analyse → Retrain smarter

Key design choices:
  - feature_snapshot (JSONB): stores the exact indicator values at prediction time
    so we can later ask "what feature values correlate with correct predictions?"
  - market_regime_at_prediction: lets us compute regime-conditional accuracy
    (e.g. XGBoost is 61% accurate in trending markets, 48% in choppy ones)
  - Deduplication: one prediction per (symbol, timeframe, prediction_date)
    so a heavily-used symbol doesn't create thousands of identical rows per day
"""

from sqlalchemy import (
    Column, BigInteger, Integer, String, Float, Boolean,
    DateTime, Date, Text, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.database import Base


class MLPrediction(Base):
    __tablename__ = "ml_predictions"

    id = Column(BigInteger, primary_key=True, index=True)

    # ── What was predicted ────────────────────────────────────────────────────
    symbol           = Column(String(20),  nullable=False)
    timeframe        = Column(String(10),  nullable=False)   # '1h','4h','1d','1wk','1mo'
    model_name       = Column(String(30),  nullable=False)   # 'xgboost','logistic','ensemble'
    mlflow_run_id    = Column(String(100), nullable=True)    # links to exact trained model version

    predicted_at     = Column(DateTime(timezone=True), nullable=False)
    prediction_date  = Column(Date, nullable=False)          # date part of predicted_at (for dedup)
    predicted_direction = Column(Integer, nullable=False)    # 1 = UP, 0 = DOWN
    confidence       = Column(Float, nullable=False)         # probability of predicted class (0.5–1.0)
    expected_return  = Column(Float, nullable=True)          # model's estimated return magnitude

    horizon_periods  = Column(Integer, nullable=False)       # how many periods ahead
    horizon_ends_at  = Column(DateTime(timezone=True), nullable=False)  # predicted_at + horizon

    price_at_prediction = Column(Float, nullable=False)      # actual price when prediction was made

    # ── What actually happened (filled in by outcome_resolver cron) ───────────
    price_at_outcome    = Column(Float,    nullable=True)
    actual_direction    = Column(Integer,  nullable=True)    # 1 = went UP, 0 = DOWN
    actual_return       = Column(Float,    nullable=True)    # actual % return over horizon
    was_correct         = Column(Boolean,  nullable=True)    # predicted_direction == actual_direction
    outcome_resolved_at = Column(DateTime(timezone=True), nullable=True)

    # ── Context snapshot at prediction time ──────────────────────────────────
    # Stored as JSONB so we can later query e.g. "show me all predictions where rsi_14 < 30"
    feature_snapshot             = Column(JSONB, nullable=True)
    macro_score_at_prediction    = Column(Float, nullable=True)
    vix_at_prediction            = Column(Float, nullable=True)
    market_regime_at_prediction  = Column(String(30), nullable=True)  # 'goldilocks','risk-off',etc.

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Core deduplication: one prediction per symbol + timeframe + calendar day.
        # Prevents the same signal being logged 100x a day for popular tickers.
        UniqueConstraint(
            "symbol", "timeframe", "prediction_date",
            name="uq_ml_prediction_symbol_tf_date",
        ),
        # Fast lookup of pending outcomes (the resolver's main query)
        Index("idx_mlpred_pending",       "horizon_ends_at",
              postgresql_where="outcome_resolved_at IS NULL"),
        # Per-symbol accuracy queries
        Index("idx_mlpred_symbol_tf",     "symbol", "timeframe"),
        # Correctness analysis
        Index("idx_mlpred_correct",       "was_correct", "symbol"),
        # Regime-conditional accuracy
        Index("idx_mlpred_regime",        "market_regime_at_prediction"),
        # Chronological queries
        Index("idx_mlpred_predicted_at",  "predicted_at"),
    )
