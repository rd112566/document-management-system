# Intelligent Document Management System with Azure OpenAI RAG

An enterprise-grade, full-stack Document Management System (DMS) powered by Retrieval-Augmented Generation (RAG) and **Azure OpenAI GPT Models** (GPT-4o, GPT-4o-mini, GPT-4, GPT-3.5).

Users can upload documents in various formats (PDF, DOCX, TXT, Markdown, Excel, CSV, JSON), automatically extract and index content with page-level metadata into **ChromaDB**, and ask questions to fetch grounded answers with precise source citations.

---

## 🌟 Key Features

1. **Multi-Format Document Ingestion & Extraction**:
   - **PDF**: Fast extraction with PyMuPDF (`fitz`), preserving page numbers and table text, with automatic OCR fallback.
   - **Word (`.docx`, `.doc`)**: Paragraphs, section headers, bullet lists, and tables with column alignment.
   - **Spreadsheets (`.xlsx`, `.csv`, `.tsv`)**: Structured row-by-row cell data formatted for LLM readability.
   - **Text & Code (`.txt`, `.md`, `.json`)**: Structured logical sections and clean pretty-printed JSON.

2. **Azure OpenAI GPT Model Deployments**:
   - First-class support for Azure OpenAI Service deployments: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-4`, `gpt-35-turbo`, or custom fine-tuned deployments.
   - Dual-mode calling engine: Official `openai.AzureOpenAI` client + direct Azure REST fallback.
   - In-app **Azure OpenAI Settings Panel**: Configure Endpoint, Key, Deployment Name, and API Version directly from the web interface, or configure via `.env`.
   - **Live Connection Testing**: Instant latency ping and deployment validation.

3. **High-Accuracy Vector Search & Citations**:
   - ChromaDB persistent storage with user-isolated vector collections.
   - Sentence-aware sliding chunking preserving context and page numbers.
   - Grounded RAG prompting: Answers strictly cite source document name and page number, with interactive expandable quote snippets.
   - Negative constraint: If the answer is not present in the uploaded document, the system explicitly informs the user instead of hallucinating.

4. **Executive Summarization & Chunk Inspection**:
   - One-click executive summary generation powered by Azure OpenAI GPT models.
   - Extracted chunk inspector to view how documents were split and indexed.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+ (installed in `backend/venv`)
- Node.js 18+ and npm

### 1. Configure Azure OpenAI

You can either configure your credentials in `backend/.env` or configure them directly in the UI later:

```env
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-08-01-preview
```

### 2. Start Both Services (1-Click)
Double-click `start_all.bat` in the root folder, or start them individually:

**Option A: Backend Only**
Double-click `run_backend.bat` or run:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --port 8000
```
- API Root: `http://127.0.0.1:8000/`
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`

**Option B: Frontend Only**
Double-click `run_frontend.bat` or run:
```powershell
cd frontend
npm run dev
```
- Web Application: `http://localhost:5173/`

---

## 📖 Prompts & Benchmarks Catalog

See [`PROMPTS.md`](PROMPTS.md) for the complete prompt engineering documentation:
- Grounded System Prompt & Citation syntax (`[Document: <name>, Page <num>]`)
- Context Injection Template
- Executive Summarization Prompt
- Azure OpenAI Connectivity Ping
- 20-Question Multi-Domain Benchmark Test Suite
- Azure Reasoning Model (`gpt-5.6-luna`) parameter compatibility notes (`max_completion_tokens`)

---

## 🛠 Tech Stack

- **Frontend**: React 19, Vite, Axios, Lucide Icons, Custom Responsive CSS
- **Backend**: Python 3.10, FastAPI, Uvicorn, Pydantic v2
- **LLM Engine**: Azure OpenAI Service (GPT-4o, GPT-4o-mini, GPT-4, GPT-3.5)
- **Database**: SQLite (`dms.db`) for Users, Documents, and Chat History
- **Authentication**: JWT tokens (PyJWT) with bcrypt password hashing
- **Text Extraction**: PyMuPDF, python-docx, openpyxl, CSV parser
- **Vector Store**: ChromaDB (`PersistentClient`) with user-isolated collections

---

## 📁 Project Structure

```text
dms/
├── backend/
│   ├── chroma_db/            # ChromaDB persistent vector storage
│   ├── uploads/              # User-uploaded files isolated by user_id
│   ├── auth.py               # Bcrypt password hashing & JWT token validation
│   ├── database.py           # SQLite connection and table schemas
│   ├── extractor.py          # PDF, DOCX, TXT, MD, CSV, XLSX, JSON text extraction
│   ├── rag_service.py        # Chunking, embeddings, ChromaDB search, Azure OpenAI QA & citations
│   ├── main.py               # FastAPI routes, Azure config & test endpoints
│   ├── requirements.txt      # Python dependencies including openai and chromadb
│   └── .env.example          # Azure OpenAI configuration template
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AuthModal.jsx        # Login & Signup forms
│   │   │   ├── Navbar.jsx           # Header with user profile & Azure OpenAI status
│   │   │   ├── AzureConfigModal.jsx # In-app Azure OpenAI configuration & test ping
│   │   │   ├── DocumentUpload.jsx   # Drag-and-drop file upload with progress bar
│   │   │   ├── DocumentList.jsx     # Document management, chunk inspector, summary
│   │   │   └── ChatInterface.jsx    # Multi-turn Q&A, citations with snippet expander
│   │   ├── context/
│   │   │   └── AuthContext.jsx      # User authentication state
│   │   ├── services/
│   │   │   └── api.js               # Axios instance with JWT interceptor
│   │   ├── App.jsx                  # Main application dashboard
│   │   └── App.css                  # Modern UI styles
│   └── package.json
├── samples/                         # Pre-generated sample documents for testing
├── run_backend.bat                  # 1-click backend launcher
└── run_frontend.bat                 # 1-click frontend launcher
```
