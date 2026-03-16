"""
scripts/migrate_portfolio_fields.py

Adds the new extended metadata columns to the portfolios table.
Safe to run multiple times — uses ADD COLUMN IF NOT EXISTS.

Run once:
    cd backend && python scripts/migrate_portfolio_fields.py
"""
import sys
from pathlib import Path

# Make sure app imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text
from app.db.database import engine  # sync engine

COLUMNS = [
    ("strategy_tag",   "VARCHAR(32)"),
    ("risk_tolerance", "VARCHAR(16)"),
    ("base_currency",  "VARCHAR(8)  DEFAULT 'USD'"),
    ("horizon",        "VARCHAR(16)"),
    ("notes",          "TEXT"),
    ("target_return",  "FLOAT"),
    ("benchmark",      "VARCHAR(20)"),
]

def run():
    with engine.connect() as conn:
        for col_name, col_type in COLUMNS:
            sql = f"ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS {col_name} {col_type};"
            conn.execute(text(sql))
            print(f"  ✓  {col_name}  {col_type}")
        conn.commit()
    print("\n✅  Migration complete.")

if __name__ == "__main__":
    print("Adding extended portfolio metadata columns…")
    run()
