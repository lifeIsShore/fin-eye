import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

try:
    from app.db.database import Base, engine, init_db
    import app.models
    
    print("Consolidating metadata...")
    print(f"Registered tables: {list(Base.metadata.tables.keys())}")
    
    # Try to create only 'users' first
    if 'users' in Base.metadata.tables:
        print("Creating 'users' table specifically...")
        Base.metadata.tables['users'].create(bind=engine, checkfirst=True)
        print("'users' table checked/created.")
    
    print("Running full create_all()...")
    Base.metadata.create_all(bind=engine)
    print("Full create_all() complete.")
    
except Exception as e:
    import traceback
    traceback.print_exc()
