import psycopg2
try:
    conn = psycopg2.connect(
        dbname="fin_eye",
        user="postgres",
        password="postgres",
        host="localhost",
        port="5432"
    )
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tables = cur.fetchall()
    print("Tables in 'public' schema:")
    for t in tables:
        print(f" - {t[0]}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
