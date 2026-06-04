import sqlite3
import json

conn = sqlite3.connect('spatial_rag.db')
cursor = conn.cursor()

# Grab the text and spatial map for the very first page
cursor.execute("SELECT full_text, spatial_map FROM document_pages WHERE id = 1")
row = cursor.fetchone()

if row:
    full_text, spatial_map_str = row
    spatial_map = json.loads(spatial_map_str)
    
    print("--- RAW TEXT EXTRACTED FOR PAGE 1 ---")
    print(full_text[:500]) # Print first 500 characters
    print("\n--- SAMPLE GEOMETRY (First 3 Words) ---")
    for word_info in spatial_map[:3]:
        print(word_info)

conn.close()