# Intelligent Document Management System with RAG

A full-stack, enterprise-grade Document Management System (DMS) powered by Retrieval-Augmented Generation (RAG). Users can upload documents (PDF, DOCX, TXT), automatically extract and index content with page-level metadata into ChromaDB, and query documents with source citations.

---

## 🚀 Quick Start Guide

### 1. Start the Backend (Terminal 1)
Double-click `run_backend.bat` or run in PowerShell:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
```
- API Health & Root: `http://127.0.0.1:8000/`
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`

### 2. Start the Frontend (Terminal 2)
Double-click `run_frontend.bat` or run in PowerShell:
```powershell
cd frontend
npm run dev
```
- Web Application: `http://localhost:5173/`

---

## 🛠 Tech Stack

- **Frontend**: React 19, Vite, Axios, Lucide Icons, Custom Responsive CSS
- **Backend**: Python 3.13, FastAPI, Uvicorn, Pydantic
- **Database**: SQLite (`dms.db`) for Users, Documents, and Chat History
- **Authentication**: JWT tokens (PyJWT) with salted password hashing (bcrypt)
- **Text Extraction**: PyMuPDF (`fitz`), `python-docx`, with Tesseract OCR fallback
- **Vector Store**: ChromaDB (`PersistentClient`) with user-isolated collections
- **RAG Engine**: Page-level sliding chunking, cosine retrieval, strict context answering, and source citations

---

## 📁 Project Structure

```text
dms/
├── backend/
│   ├── chroma_db/            # ChromaDB persistent vector storage
│   ├── uploads/              # User-uploaded files isolated by user_id
│   ├── auth.py               # Bcrypt password hashing & JWT token validation
│   ├── database.py           # SQLite connection and table schemas
│   ├── extractor.py          # PyMuPDF, python-docx, OCR fallback
│   ├── rag_service.py        # Chunking, embeddings, ChromaDB search, answering & citations
│   ├── main.py               # FastAPI routes and middleware
│   ├── requirements.txt      # Python dependencies
│   └── generate_samples.py   # Script to generate sample PDF/DOCX/TXT
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AuthModal.jsx       # Login & Signup forms
│   │   │   ├── Navbar.jsx          # Header with user profile & navigation
│   │   │   ├── DocumentUpload.jsx  # Drag-and-drop file upload with progress bar
│   │   │   ├── DocumentList.jsx    # Document management (download, rename, delete, summary)
│   │   │   └── ChatInterface.jsx   # Multi-turn Q&A, citations with snippet expander
│   │   ├── context/
│   │   │   └── AuthContext.jsx     # User authentication state
│   │   ├── services/
│   │   │   └── api.js              # Axios instance with JWT interceptor
│   │   ├── App.jsx                 # Main application dashboard
│   │   └── App.css                 # Clean modern styling
│   └── package.json
├── samples/                  # Pre-generated sample documents for testing
├── run_backend.bat           # 1-click backend launcher
└── run_frontend.bat          # 1-click frontend launcher
```

---

## 🧪 20 Evaluation Questions (Demo & Testing)

Using the included files in `samples/` (`quantum_computing_overview.pdf`, `sample_ai_policy.txt`, `project_requirements.docx`):

1. *What did Google Quantum AI demonstrate in 2019?* (Expected: 53-qubit Sycamore processor, Page 1 citation)
2. *What speedup does Grover's algorithm provide?* (Expected: Quadratic speedup for database search, Page 2 citation)
3. *What algorithm can factor large integers exponentially faster?* (Expected: Shor's algorithm, Page 2 citation)
4. *How many physical qubits are needed per logical qubit in fault-tolerant computing?* (Expected: Thousands of physical qubits, Page 2 citation)
5. *What encryption standard is required by the AI policy?* (Expected: AES-256 standard, Page 1 citation)
6. *How long can authentication tokens last before expiring?* (Expected: 24 hours)
7. *Does the AI policy allow User A to see User B's documents?* (Expected: No, strict user data isolation)
8. *What must accompany every factual statement in RAG answers?* (Expected: Document name and page number)
9. *What is the project budget specified in the requirements?* (Expected: Open-Source)
10. *What file formats must the document extraction support?* (Expected: PDF, DOCX, and TXT)
11. *What vector store is specified in the requirements?* (Expected: ChromaDB)
12. *What is the deadline mentioned in the project specification?* (Expected: November 2026)
13. *What is a qubit's superposition state?* (Expected: Linear combination of states)
14. *What type of codes are required for error correction?* (Expected: Surface codes)
15. *What should the system say if an answer is not in the documents?* (Expected: State that the answer is not found)
16. *Who is the President of Mars?* (Negative test - should reply "not found in uploaded documents")
17. *What is the recipe for chocolate cake?* (Negative test - should reply "not found")
18. *Summarize the AI Governance Policy.* (Tests summary capabilities)
19. *Summarize the Quantum Computing Overview.* (Tests multi-page summary)
20. *What are the three main deliverables of the project?* (Cross-referencing list items from DOCX)
