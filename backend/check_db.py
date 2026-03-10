"""Check DB tables and alembic state - writes to log file."""
import sys

try:
    from sqlalchemy import create_engine, text
    
    engine = create_engine('postgresql://postgres:postgres@localhost:5432/fin_eye')
    with engine.connect() as conn:
        tables = conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
        )).fetchall()
        table_names = [t[0] for t in tables]
        
        # Check alembic version
        try:
            vers = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
            alembic_vers = [v[0] for v in vers]
        except Exception as e:
            alembic_vers = f"ERROR: {e}"
    
    with open("db_state.log", "w") as f:
        f.write(f"Tables: {table_names}\n")
        f.write(f"Alembic versions: {alembic_vers}\n")
    print("Written to db_state.log")

except Exception as e:
    with open("db_state.log", "w") as f:
        f.write(f"FATAL ERROR: {e}\n")
    print(f"Error: {e}")
