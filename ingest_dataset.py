import os
import sqlite3
import json
import pytesseract
from PIL import Image

# Default 64-bit installation path:
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Configuration
DATASET_DIR = "./dataset/images"  # Path to your folder containing 1.png to 199.png
DB_PATH = "spatial_rag.db"

def ingest_all_images():
    # 1. Connect to our database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 2. Get a sorted list of your images (page (1).png to page (199).png)
    image_files = [f for f in os.listdir(DATASET_DIR) if f.endswith('.png')]
    
    # This splits the string by the opening parenthesis '(' and closing parenthesis ')' 
    # to extract just the number inside, ensuring perfect numerical order.
    image_files.sort(key=lambda x: int(x.split('(')[1].split(')')[0]))
    
    print(f"Found {len(image_files)} images in '{DATASET_DIR}'. Starting OCR ingestion...\n")

    for file_name in image_files:
        file_path = os.path.join(DATASET_DIR, file_name)
        
        try:
            # 3. Open image and run Tesseract to get structured data
            img = Image.open(file_path)
            ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            
            page_words = []
            spatial_map = []
            
            # Counters for logging telemetry
            words_found = 0
            words_neglected = 0
            
            # 4. Parse out the TBLR coordinates for every single word
            for i in range(len(ocr_data['text'])):
                word = ocr_data['text'][i].strip()
                confidence = int(ocr_data['conf'][i])
                
                # Check if the text element is empty or filtered by confidence threshold
                if word and confidence > 40:
                    words_found += 1
                    page_words.append(word)
                    
                    left = ocr_data['left'][i]
                    top = ocr_data['top'][i]
                    width = ocr_data['width'][i]
                    height = ocr_data['height'][i]
                    
                    # Convert to standard absolute TBLR coordinates
                    spatial_map.append({
                        "word": word,
                        "top": top,
                        "bottom": top + height,
                        "left": left,
                        "right": left + width
                    })
                else:
                    # Increment if it's empty space or low confidence noise
                    words_neglected += 1
            
            # Combine individual words into a single full-text string for fast retrieval
            full_text = " ".join(page_words)
            
            # 5. Insert into the 'documents' table
            cursor.execute(
                "INSERT INTO documents (file_name, file_path) VALUES (?, ?)",
                (file_name, file_path)
            )
            document_id = cursor.lastrowid  # Grab the auto-incremented ID
            
            # 6. Insert into the 'document_pages' table (serialize spatial_map list to JSON string)
            cursor.execute(
                "INSERT INTO document_pages (document_id, page_number, full_text, spatial_map) VALUES (?, ?, ?, ?)",
                (document_id, 1, full_text, json.dumps(spatial_map))
            )
            
            # Multi-line console telemetry log
            print(f"--- [Page Completed] ---")
            print(f"File: {file_name}")
            print(f"Status: Saved & Indexed successfully.")
            print(f"Metrics: {words_found} words accepted | {words_neglected} words neglected (noise/empty)\n")
            
        except Exception as e:
            print(f"❌ Error processing {file_name}: {e}\n")
            
    # Commit changes and clean up connection
    conn.commit()
    conn.close()
    print("All 199 images successfully parsed and saved to the database!")

if __name__ == "__main__":
    ingest_all_images()