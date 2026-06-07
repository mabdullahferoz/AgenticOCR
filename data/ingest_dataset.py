import warnings
warnings.filterwarnings("ignore", category=UserWarning)
import os
import sqlite3
import json
import difflib
import re
from PIL import Image
import easyocr

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
DB_PATH = os.path.join(BASE_DIR, "spatial_rag.db")

def get_closest_database_match(failed_word: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT full_text FROM document_pages")
    all_rows = cursor.fetchall()
    conn.close()
    vocabulary = set()
    for row in all_rows:
        if row[0]:
            words = [w.strip(".,;:!?()[]\"'").upper() for w in row[0].split()]
            vocabulary.update(words)
    closest_matches = difflib.get_close_matches(failed_word.upper(), list(vocabulary), n=1, cutoff=0.5)
    return closest_matches[0] if closest_matches else None

def ingest_all_images():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    reader = easyocr.Reader(['en'], gpu=False)
    
    if not os.path.exists(DATASET_DIR):
        print("Dataset directory does not exist.")
        return

    books = [d for d in os.listdir(DATASET_DIR) if os.path.isdir(os.path.join(DATASET_DIR, d))]
    print(f"Found {len(books)} books. Running deduplicated OCR Ingestion pipeline...\n")

    for book_name in books:
        book_dir = os.path.join(DATASET_DIR, book_name)
        image_files = [f for f in os.listdir(book_dir) if os.path.isfile(os.path.join(book_dir, f))]
        
        # Try to sort logically if they match 'page (N)'
        def get_page_num(f):
            m = re.search(r'\((\d+)\)', f)
            return int(m.group(1)) if m else 999999
        image_files.sort(key=get_page_num)

        # Check or insert book
        cursor.execute("SELECT id FROM documents WHERE LOWER(file_name) = ?", (book_name.lower(),))
        existing_doc = cursor.fetchone()
        if existing_doc:
            document_id = existing_doc[0]
        else:
            cursor.execute("INSERT INTO documents (file_name, file_path) VALUES (?, ?)", (book_name, book_dir))
            document_id = cursor.lastrowid

        for idx, file_name in enumerate(image_files):
            file_path = os.path.join(book_dir, file_name)
            
            try:
                # determine page number
                m = re.search(r'\((\d+)\)', file_name)
                page_num = int(m.group(1)) if m else idx + 1

                # Check if page exists
                cursor.execute("SELECT id FROM document_pages WHERE document_id = ? AND page_file_name = ?", (document_id, file_name))
                if cursor.fetchone():
                    print(f"⏭️ [Skipped] -> '{book_name}/{file_name}' is already indexed.")
                    continue

                print(f"Ingesting '{book_name}/{file_name}'...")
                # OCR
                result = reader.readtext(file_path)
                
                page_words, spatial_map = [], []
                words_found, words_neglected = 0, 0
                
                for (box, word, confidence) in result:
                    word = word.strip()
                    conf_pct = confidence * 100
                    
                    if word and conf_pct > 40:
                        words_found += 1
                        page_words.append(word)
                        
                        left = float(min([pt[0] for pt in box]))
                        right = float(max([pt[0] for pt in box]))
                        top = float(min([pt[1] for pt in box]))
                        bottom = float(max([pt[1] for pt in box]))
                        
                        spatial_map.append({
                            "word": word, "top": top, "bottom": bottom,
                            "left": left, "right": right
                        })
                    else:
                        words_neglected += 1
                full_text = " ".join(page_words)
                
                # Insert page
                cursor.execute(
                    "INSERT INTO document_pages (document_id, page_number, page_file_name, full_text, spatial_map) VALUES (?, ?, ?, ?, ?)",
                    (document_id, page_num, file_name, full_text, json.dumps(spatial_map))
                )
                print(f"--- [Page Completed] --- File: {book_name}/{file_name} Metrics: {words_found} accepted | {words_neglected} neglected\n")
                
            except Exception as e:
                print(f"❌ Error processing {book_name}/{file_name}: {e}\n")
            
    conn.commit()
    conn.close()
    print("Deduplicated database catalog synchronization successfully complete!")

if __name__ == "__main__":
    ingest_all_images()