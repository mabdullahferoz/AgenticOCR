import os
import sqlite3
import json
import difflib
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset", "images")
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
    image_files = [f for f in os.listdir(DATASET_DIR) if f.endswith('.png')]
    image_files.sort(key=lambda x: int(x.split('(')[1].split(')')[0]))
    print(f"Found {len(image_files)} images. Running deduplicated OCR Ingestion pipeline...\n")

    for file_name in image_files:
        file_path = os.path.join(DATASET_DIR, file_name)
        try:
            # Check if this file page is already registered to avoid redundant OCR computation costs!
            cursor.execute("SELECT id FROM documents WHERE file_name = ?", (file_name,))
            existing_doc = cursor.fetchone()
            
            if existing_doc:
                document_id = existing_doc[0]
                # Check if the page entry also exists
                cursor.execute("SELECT id FROM document_pages WHERE document_id = ? AND page_number = 1", (document_id,))
                if cursor.fetchone():
                    print(f"⏭️ [Skipped] -> '{file_name}' is already indexed in the spatial catalog.")
                    continue

            # If not skipped, compute the heavy OCR data slice
            img = Image.open(file_path)
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
            
            # Using INSERT OR IGNORE to respect our unique naming boundaries safely
            cursor.execute("INSERT OR IGNORE INTO documents (file_name, file_path) VALUES (?, ?)", (file_name, file_path))
            document_id = cursor.lastrowid
            
            # If it was an ignore event, fetch the pre-existing fallback ID pointer row
            if document_id is None or document_id == 0:
                cursor.execute("SELECT id FROM documents WHERE file_name = ?", (file_name,))
                document_id = cursor.fetchone()[0]

            # Insert page with constraint protection rules applied
            cursor.execute("INSERT OR IGNORE INTO document_pages (document_id, page_number, full_text, spatial_map) VALUES (?, ?, ?, ?)",
                           (document_id, 1, full_text, json.dumps(spatial_map)))
            print(f"--- [Page Completed] --- File: {file_name} Metrics: {words_found} accepted | {words_neglected} neglected\n")
            
        except Exception as e:
            print(f"❌ Error processing {file_name}: {e}\n")
            
    conn.commit()
    conn.close()
    print("Deduplicated database catalog synchronization successfully complete!")

if __name__ == "__main__":
    ingest_all_images()