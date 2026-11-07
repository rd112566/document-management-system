import os
import shutil
import uuid
from database import get_db_connection, init_db
from extractor import extract_document_text
from rag_service import index_document, delete_document_from_index

init_db()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "samples")

target_pdfs = [
    "OM - Unit II.pdf",
    "OM  Unit 4 Notes.pdf",
    "OM - Unit V.pdf"
]

def ingest_samples_for_user(user_id: int = 1):
    conn = get_db_connection()
    user_dir = os.path.join(UPLOAD_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)

    for pdf_name in target_pdfs:
        src_path = os.path.join(SAMPLES_DIR, pdf_name)
        if not os.path.exists(src_path):
            print(f"File not found: {src_path}")
            continue

        # Check if already in DB
        existing = conn.execute(
            "SELECT id, original_name FROM documents WHERE user_id = ? AND original_name = ?",
            (user_id, pdf_name)
        ).fetchone()

        if existing:
            print(f"Document already indexed: {pdf_name} (ID: {existing['id']})")
            continue

        saved_filename = f"{uuid.uuid4().hex}_{pdf_name}"
        dest_path = os.path.join(user_dir, saved_filename)
        shutil.copyfile(src_path, dest_path)
        file_size = os.path.getsize(dest_path)

        # Extract text
        print(f"\nProcessing & Extracting text from: {pdf_name}...")
        pages_data = extract_document_text(dest_path, "pdf")
        page_count = len(pages_data)

        # Save to DB
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO documents (user_id, original_name, saved_filename, file_type, file_size, page_count)
            VALUES (?, ?, ?, 'pdf', ?, ?)
        """, (user_id, pdf_name, saved_filename, file_size, page_count))
        doc_id = cursor.lastrowid
        conn.commit()

        # Index in ChromaDB
        chunks = index_document(user_id=user_id, doc_id=doc_id, filename=pdf_name, pages_data=pages_data)
        print(f"Indexed '{pdf_name}' (ID: {doc_id}) -> {page_count} pages, {chunks} chunks embedded in ChromaDB.")

    conn.close()
    print("\nAll sample units successfully ingested and indexed!")

if __name__ == "__main__":
    ingest_samples_for_user(user_id=1)
