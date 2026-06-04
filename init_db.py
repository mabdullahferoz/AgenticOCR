import sqlite3

def initialize_database():
    # Connect to SQLite (it will create the file if it doesn't exist)
    conn = sqlite3.connect('spatial_rag.db')
    cursor = conn.cursor()
    
    # 1. Create the Documents Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL
        )
    ''')
    
    # 2. Create the Document Pages Table with text and spatial JSON metadata
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS document_pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            page_number INTEGER DEFAULT 1,
            full_text TEXT,
            spatial_map TEXT, -- We will store our JSON array as a text string here
            FOREIGN KEY (document_id) REFERENCES documents (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully with 'documents' and 'document_pages' tables.")

if __name__ == "__main__":
    initialize_database()