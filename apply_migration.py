import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    print("DATABASE_URL not found in .env")
    exit(1)

try:
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    
    sql = "ALTER TABLE toppings ADD COLUMN disponible BOOLEAN DEFAULT TRUE;"
    print(f"Executing: {sql}")
    cur.execute(sql)
    
    conn.commit()
    cur.close()
    conn.close()
    print("Migration applied successfully!")
except Exception as e:
    print(f"Error applying migration: {e}")
    exit(1)
