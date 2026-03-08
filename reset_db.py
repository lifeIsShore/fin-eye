import psycopg2
try:
    conn = psycopg2.connect(
        dbname="fin_eye",
        user="postgres",
        password="postgres",
        host="localhost",
        port="5432"
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    # Drop all tables in public schema
    print("Dropping all tables in 'public' schema...")
    cur.execute("""
        DO $$ DECLARE
            r RECORD;
        BEGIN
            FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
            END LOOP;
        END $$;
    """)
    print("All tables dropped successfully.")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
