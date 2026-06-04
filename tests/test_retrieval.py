import sqlite3
import json
import os

# Compute path to root directory database safely
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
db_file = os.path.join(BASE_DIR, "spatial_rag.db")

if not os.path.exists(db_file):
    print(f"❌ Error: Cannot run validation test. '{db_file}' is missing from root.")
else:
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Grab the text and spatial map for the very first page row entries
    cursor.execute("SELECT full_text, spatial_map FROM document_pages LIMIT 1")
    row = cursor.fetchone()

    if row:
        full_text, spatial_map_str = row
        spatial_map = json.loads(spatial_map_str)
        
        print("--- RAW TEXT EXTRACTED FOR PAGE 1 ---")
        print(full_text[:500] + "...") 
        print("\n--- SAMPLE GEOMETRY (First 3 Words) ---")
        for word_info in spatial_map[:3]:
            print(word_info)
    else:
        print("⚠ Database file found, but 'document_pages' table appears to be empty.")

    conn.close()