import sqlite3
import os

# Compute path to root directory database safely
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
db_file = os.path.join(BASE_DIR, "spatial_rag.db")

if not os.path.exists(db_file):
    print(f"❌ Error: '{db_file}' file does not exist in the root workspace directory yet.")
else:
    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = c.fetchall()
    print("Tables found in database:", tables)
    
    for table in tables:
        t_name = table[0]
        if t_name != 'sqlite_sequence':
            c.execute(f"SELECT COUNT(*) FROM {t_name}")
            print(f" -> Table '{t_name}' contains: {c.fetchone()[0]} rows.")
    conn.close()