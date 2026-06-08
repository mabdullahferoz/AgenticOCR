import sqlite3
import json
import os
import re
from collections import Counter
from pypdf import PdfReader
import jiwer
import Levenshtein

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'spatial_rag.db')
PDF_PATH = os.path.join(os.path.dirname(__file__), 'AnimalFarm.pdf')
OUTPUT_JSON = os.path.join(os.path.dirname(__file__), 'metrics.json')

def normalize_text(text):
    # Lowercase and remove non-alphanumeric characters for word matching and error rates
    # Keep spaces
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_ocr_text():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Fetch all pages across all documents (Book 1 to Book 6)
    cursor.execute("""
        SELECT p.full_text 
        FROM document_pages p
        JOIN documents d ON p.document_id = d.id
        ORDER BY d.file_name, p.page_number
    """)
    pages = cursor.fetchall()
    conn.close()
    
    full_ocr_text = " ".join([page[0] for page in pages if page[0]])
    return full_ocr_text

def get_pdf_text():
    reader = PdfReader(PDF_PATH)
    full_pdf_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_pdf_text.append(text)
    return " ".join(full_pdf_text)

def main():
    print("Extracting OCR Text from Database...")
    ocr_raw = get_ocr_text()
    print("Extracting Ground Truth Text from PDF...")
    pdf_raw = get_pdf_text()
    
    print("Normalizing texts...")
    ocr_norm = normalize_text(ocr_raw)
    pdf_norm = normalize_text(pdf_raw)
    
    ocr_words = ocr_norm.split()
    pdf_words = pdf_norm.split()
    
    # Counts
    ocr_word_count = len(ocr_words)
    pdf_word_count = len(pdf_words)
    ocr_char_count = len(ocr_raw)
    pdf_char_count = len(pdf_raw)
    
    # Frequencies
    ocr_freq = Counter(ocr_words)
    pdf_freq = Counter(pdf_words)
    
    # Prepare combined frequency table
    all_unique_words = set(ocr_freq.keys()).union(set(pdf_freq.keys()))
    word_freq_table = []
    for word in all_unique_words:
        word_freq_table.append({
            "word": word,
            "pdf_count": pdf_freq.get(word, 0),
            "ocr_count": ocr_freq.get(word, 0)
        })
    # Sort by frequency in PDF descending, then OCR
    word_freq_table.sort(key=lambda x: (x["pdf_count"], x["ocr_count"]), reverse=True)
    
    # Levenshtein & Similarity
    print("Calculating Levenshtein Distance...")
    lev_distance = Levenshtein.distance(pdf_norm, ocr_norm)
    max_len = max(len(pdf_norm), len(ocr_norm))
    lev_similarity_pct = ((max_len - lev_distance) / max_len) * 100 if max_len > 0 else 100
    
    # Jaccard Similarity on unique words
    print("Calculating Jaccard Similarity...")
    intersection = len(set(ocr_words).intersection(set(pdf_words)))
    union = len(set(ocr_words).union(set(pdf_words)))
    jaccard_similarity = (intersection / union) * 100 if union > 0 else 100
    
    # Character Error Rate (CER) & Word Error Rate (WER)
    print("Calculating CER and WER using jiwer...")
    try:
        wer = jiwer.wer(pdf_norm, ocr_norm)
        cer = jiwer.cer(pdf_norm, ocr_norm)
    except Exception as e:
        print(f"Jiwer calculation failed (possibly empty string): {e}")
        wer = 0.0
        cer = 0.0

    # Build Output
    metrics = {
        "counts": {
            "pdf_word_count": pdf_word_count,
            "ocr_word_count": ocr_word_count,
            "word_count_diff_pct": round(abs(pdf_word_count - ocr_word_count) / max(pdf_word_count, 1) * 100, 2),
            "pdf_char_count": pdf_char_count,
            "ocr_char_count": ocr_char_count,
            "char_count_diff_pct": round(abs(pdf_char_count - ocr_char_count) / max(pdf_char_count, 1) * 100, 2),
        },
        "quality": {
            "wer_pct": round(wer * 100, 2),
            "cer_pct": round(cer * 100, 2),
            "levenshtein_distance": lev_distance,
            "levenshtein_similarity_pct": round(lev_similarity_pct, 2),
            "jaccard_similarity_pct": round(jaccard_similarity, 2)
        },
        "word_frequencies": word_freq_table
    }
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=4)
    print(f"Metrics successfully saved to {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
