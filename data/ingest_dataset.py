import os
import sqlite3
import json
import difflib
import pytesseract
import re
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
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
                img = Image.open(file_path).convert('L')
                ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                
                page_words, spatial_map = [], []
                words_found, words_neglected = 0, 0
                
                for i in range(len(ocr_data['text'])):
                    word = ocr_data['text'][i].strip()
                    confidence = int(ocr_data['conf'][i]) if ocr_data['conf'][i] != '-1' else 0
                    if word and confidence > 40:
                        words_found += 1
                        page_words.append(word)
                        spatial_map.append({
                            "word": word, "top": ocr_data['top'][i], "bottom": ocr_data['top'][i] + ocr_data['height'][i],
                            "left": ocr_data['left'][i], "right": ocr_data['left'][i] + ocr_data['width'][i]
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