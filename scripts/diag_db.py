import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

try:
    from app.config import settings
    from app.db.database import Base, engine, init_db
    print(f"Tables before import: {list(Base.metadata.tables.keys())}")
    
    import app.models
    print(f"Tables after import: {list(Base.metadata.tables.keys())}")
    
    print("Attempting init_db()...")
    if init_db():
        print("init_db() returned True")
        # Check if tables exist in the DB
        from sqlalchemy import inspect
        inspector = inspect(engine)
        print(f"Tables in DB: {inspector.get_table_names()}")
    else:
        print("init_db() returned False")
except Exception as e:
    import traceback
    print("Caught Exception:")
    traceback.print_exc()
