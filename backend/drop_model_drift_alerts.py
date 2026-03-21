import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(".env")
url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/fin_eye")
engine = create_engine(url)

try:
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS model_drift_alerts CASCADE;"))
    print("Dropped model_drift_alerts table successfully.")
except Exception as e:
    print(f"Error: {e}")
