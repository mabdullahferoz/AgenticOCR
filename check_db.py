import sqlite3

conn = sqlite3.connect('spatial_rag.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
print("Tables found in database:", c.fetchall())
conn.close()