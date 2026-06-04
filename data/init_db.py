import sqlite3
import os

def initialize_database():
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    db_path = os.path.join(BASE_DIR, 'spatial_rag.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Added UNIQUE(file_name) constraint to prevent duplicate file records
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            file_name TEXT NOT NULL UNIQUE, 
            file_path TEXT NOT NULL
        )
    ''')
    
    # 2. Added UNIQUE(document_id, page_number) to prevent duplicating pages within the same document
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS document_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            document_id INTEGER, 
            page_number INTEGER DEFAULT 1,
            full_text TEXT, 
            spatial_map TEXT, 
            FOREIGN KEY (document_id) REFERENCES documents (id),
            UNIQUE(document_id, page_number)
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Database initialized successfully with UNIQUE safeguards at: {db_path}")

if __name__ == "__main__":
    initialize_database()