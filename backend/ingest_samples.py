import os
import shutil
import uuid
from database import get_db_connection, init_db
from extractor import extract_document_text
from rag_service import index_document

init_db()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "samples")

SUPPORTED_EXTENSIONS = {"pdf", "docx", "doc", "txt", "md", "csv", "xlsx", "json"}

def ensure_user_exists(conn, user_id: int = 1):
    """
    Ensures that a user with user_id exists in SQLite.
    """
    user = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        from auth import hash_password
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (id, username, email, password_hash) VALUES (?, ?, ?, ?)",
            (user_id, "demo_user", "demo@example.com", hash_password("DemoPassword123!"))
        )
        conn.commit()
        print(f"Created default demo user (ID: {user_id}, username: demo_user, password: DemoPassword123!)")

def ingest_all_samples(user_id: int = 1):
    """
    Scans the samples/ directory and ingests all supported documents into SQLite and ChromaDB.
    """
    conn = get_db_connection()
    ensure_user_exists(conn, user_id)

    user_dir = os.path.join(UPLOAD_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)

    if not os.path.exists(SAMPLES_DIR):
        print(f"Samples directory not found: {SAMPLES_DIR}")
        conn.close()
        return

    sample_files = sorted(os.listdir(SAMPLES_DIR))
    ingested_count = 0

    for filename in sample_files:
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext not in SUPPORTED_EXTENSIONS:
            continue

        src_path = os.path.join(SAMPLES_DIR, filename)
        if not os.path.isfile(src_path):
            continue

        # Check if already in DB
        existing = conn.execute(
            "SELECT id, original_name FROM documents WHERE user_id = ? AND original_name = ?",
            (user_id, filename)
        ).fetchone()

        if existing:
            print(f"[Skip] Already indexed: {filename} (Doc ID: {existing['id']})")
            continue

        saved_filename = f"{uuid.uuid4().hex}_{filename}"
        dest_path = os.path.join(user_dir, saved_filename)
        shutil.copyfile(src_path, dest_path)
        file_size = os.path.getsize(dest_path)

        # Extract text
        print(f"\nProcessing & Extracting text from: {filename} ({ext.upper()})...")
        try:
            pages_data = extract_document_text(dest_path, ext)
            page_count = len(pages_data)
        except Exception as e:
            print(f"Failed to extract {filename}: {e}")
            if os.path.exists(dest_path):
                os.remove(dest_path)
            continue

        # Save to SQLite
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO documents (user_id, original_name, saved_filename, file_type, file_size, page_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, filename, saved_filename, ext, file_size, page_count))
        doc_id = cursor.lastrowid
        conn.commit()

        # Index in ChromaDB
        chunks = index_document(user_id=user_id, doc_id=doc_id, filename=filename, pages_data=pages_data)
        print(f"-> Indexed '{filename}' (ID: {doc_id}) -> {page_count} pages, {chunks} chunks stored in ChromaDB.")
        ingested_count += 1

    conn.close()
    print(f"\nIngestion complete! Successfully added {ingested_count} new document(s) to knowledge base.")

if __name__ == "__main__":
    ingest_all_samples(user_id=1)
