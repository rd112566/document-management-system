import os
import shutil
import uuid
import json
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr

from database import init_db, get_db_connection
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)
from extractor import extract_document_text
from rag_service import (
    index_document,
    delete_document_from_index,
    query_rag,
    generate_summary
)

# Initialize Database
init_db()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="Document Management System with RAG",
    description="Enterprise RAG Backend with FastAPI, SQLite, and ChromaDB",
    version="1.0.0"
)

# Enable CORS for React Frontend
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://document-management-system-six-gamma.vercel.app",
]

# Allow custom frontend URL from env if provided
frontend_env = os.getenv("FRONTEND_URL")
if frontend_env:
    origins.append(frontend_env.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ----------------- PYDANTIC SCHEMAS -----------------
class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class QuestionRequest(BaseModel):
    question: str
    document_id: Optional[int] = None

class RenameRequest(BaseModel):
    new_name: str

# ----------------- AUTH ENDPOINTS -----------------
@app.post("/api/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(user: UserRegister):
    conn = get_db_connection()
    # Check if username or email exists
    existing = conn.execute(
        "SELECT id FROM users WHERE username = ? OR email = ?",
        (user.username, user.email)
    ).fetchone()
    if existing:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )

    hashed = hash_password(user.password)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (user.username, user.email, hashed)
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    token = create_access_token({"sub": user_id, "username": user.username})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user_id, "username": user.username, "email": user.email}
    }

@app.post("/api/auth/login")
def login(creds: UserLogin):
    conn = get_db_connection()
    user = conn.execute(
        "SELECT id, username, email, password_hash FROM users WHERE username = ?",
        (creds.username,)
    ).fetchone()
    conn.close()

    if not user or not verify_password(creds.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password. If you haven't created an account on the live app yet, please click 'Sign Up' first!"
        )

    token = create_access_token({"sub": user["id"], "username": user["username"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user["id"], "username": user["username"], "email": user["email"]}
    }

@app.get("/api/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}

# ----------------- DOCUMENT ENDPOINTS -----------------
@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if ext not in ["pdf", "docx", "doc", "txt"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported format. Only PDF, DOCX, and TXT are supported."
        )

    user_dir = os.path.join(UPLOAD_DIR, str(current_user["id"]))
    os.makedirs(user_dir, exist_ok=True)

    saved_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(user_dir, saved_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)

    # Extract text with page numbers
    try:
        pages_data = extract_document_text(file_path, ext)
        page_count = len(pages_data)
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract document text: {str(e)}"
        )

    # Save to SQLite
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documents (user_id, original_name, saved_filename, file_type, file_size, page_count)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (current_user["id"], file.filename, saved_filename, ext, file_size, page_count))
    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Index in ChromaDB
    chunks_created = index_document(
        user_id=current_user["id"],
        doc_id=doc_id,
        filename=file.filename,
        pages_data=pages_data
    )

    return {
        "id": doc_id,
        "original_name": file.filename,
        "file_type": ext,
        "file_size": file_size,
        "page_count": page_count,
        "chunks_indexed": chunks_created,
        "message": f"Successfully uploaded and indexed {chunks_created} chunks."
    }

@app.get("/api/documents")
def list_documents(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    docs = conn.execute("""
        SELECT id, original_name, file_type, file_size, page_count, upload_date
        FROM documents
        WHERE user_id = ?
        ORDER BY upload_date DESC
    """, (current_user["id"],)).fetchall()
    conn.close()
    return [dict(d) for d in docs]

@app.put("/api/documents/{doc_id}/rename")
def rename_document(
    doc_id: int,
    req: RenameRequest,
    current_user: dict = Depends(get_current_user)
):
    conn = get_db_connection()
    doc = conn.execute(
        "SELECT id FROM documents WHERE id = ? AND user_id = ?",
        (doc_id, current_user["id"])
    ).fetchone()

    if not doc:
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found")

    new_name = req.new_name.strip()
    if not new_name:
        conn.close()
        raise HTTPException(status_code=400, detail="New name cannot be empty")

    conn.execute(
        "UPDATE documents SET original_name = ? WHERE id = ?",
        (new_name, doc_id)
    )
    conn.commit()
    conn.close()
    return {"message": "Document renamed successfully", "new_name": new_name}

@app.delete("/api/documents/{doc_id}")
def delete_document(
    doc_id: int,
    current_user: dict = Depends(get_current_user)
):
    conn = get_db_connection()
    doc = conn.execute(
        "SELECT id, saved_filename FROM documents WHERE id = ? AND user_id = ?",
        (doc_id, current_user["id"])
    ).fetchone()

    if not doc:
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete physical file
    file_path = os.path.join(UPLOAD_DIR, str(current_user["id"]), doc["saved_filename"])
    if os.path.exists(file_path):
        os.remove(file_path)

    # Delete from DB
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()

    # Delete from ChromaDB
    delete_document_from_index(user_id=current_user["id"], doc_id=doc_id)

    return {"message": "Document deleted successfully"}

@app.get("/api/documents/{doc_id}/download")
def download_document(
    doc_id: int,
    current_user: dict = Depends(get_current_user)
):
    conn = get_db_connection()
    doc = conn.execute(
        "SELECT original_name, saved_filename FROM documents WHERE id = ? AND user_id = ?",
        (doc_id, current_user["id"])
    ).fetchone()
    conn.close()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = os.path.join(UPLOAD_DIR, str(current_user["id"]), doc["saved_filename"])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File on disk missing")

    return FileResponse(path=file_path, filename=doc["original_name"])

@app.post("/api/documents/{doc_id}/summary")
def get_document_summary(
    doc_id: int,
    current_user: dict = Depends(get_current_user)
):
    summary = generate_summary(user_id=current_user["id"], document_id=doc_id)
    return {"document_id": doc_id, "summary": summary}

# ----------------- CHAT & RAG ENDPOINTS -----------------
@app.post("/api/chat")
def ask_question(
    req: QuestionRequest,
    current_user: dict = Depends(get_current_user)
):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Query RAG
    rag_result = query_rag(
        user_id=current_user["id"],
        question=req.question,
        document_id=req.document_id
    )

    # Save to Chat History
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_history (user_id, document_id, question, answer, citations)
        VALUES (?, ?, ?, ?, ?)
    """, (
        current_user["id"],
        req.document_id,
        req.question,
        rag_result["answer"],
        json.dumps(rag_result["citations"])
    ))
    history_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": history_id,
        "question": req.question,
        "answer": rag_result["answer"],
        "citations": rag_result["citations"],
        "model_used": rag_result.get("model_used", "gpt-5.6-luna (Azure OpenAI)"),
        "document_id": req.document_id
    }

@app.get("/api/chat/history")
def get_chat_history(
    document_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    conn = get_db_connection()
    if document_id:
        rows = conn.execute("""
            SELECT id, question, answer, citations, created_at, document_id
            FROM chat_history
            WHERE user_id = ? AND document_id = ?
            ORDER BY created_at ASC
        """, (current_user["id"], document_id)).fetchall()
    else:
        rows = conn.execute("""
            SELECT id, question, answer, citations, created_at, document_id
            FROM chat_history
            WHERE user_id = ?
            ORDER BY created_at ASC
        """, (current_user["id"],)).fetchall()
    conn.close()

    result = []
    for r in rows:
        item = dict(r)
        try:
            item["citations"] = json.loads(item["citations"]) if item["citations"] else []
        except Exception:
            item["citations"] = []
        result.append(item)
    return result

@app.delete("/api/chat/history")
def clear_chat_history(
    document_id: Optional[int] = None,
    current_user: dict = Depends(get_current_user)
):
    conn = get_db_connection()
    if document_id:
        conn.execute("DELETE FROM chat_history WHERE user_id = ? AND document_id = ?", (current_user["id"], document_id))
    else:
        conn.execute("DELETE FROM chat_history WHERE user_id = ?", (current_user["id"],))
    conn.commit()
    conn.close()
    return {"message": "Chat history cleared"}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "Document Management System with RAG",
        "endpoints": {
            "docs": "/docs",
            "auth": "/api/auth",
            "documents": "/api/documents",
            "chat": "/api/chat"
        }
    }
