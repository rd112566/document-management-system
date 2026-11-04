import os
import re
import chromadb
from chromadb.utils import embedding_functions
import requests

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
os.makedirs(CHROMA_DIR, exist_ok=True)

# Use Chroma's default sentence transformer / ONNX embedding
client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = client.get_or_create_collection(name="dms_rag_collection")

def chunk_text(pages_data, doc_id: int, user_id: int, filename: str, chunk_size: int = 500, overlap: int = 100):
    """
    Chunks text by page while preserving document metadata and page numbers.
    """
    chunks = []
    chunk_index = 0

    for page_item in pages_data:
        page_num = page_item["page"]
        text = page_item["text"]
        
        # Clean text
        text = re.sub(r'\s+', ' ', text).strip()
        if not text or text.startswith("[Empty"):
            continue

        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunk_str = text[start:end].strip()
            
            if len(chunk_str) > 20:
                chunks.append({
                    "id": f"user_{user_id}_doc_{doc_id}_chunk_{chunk_index}",
                    "text": chunk_str,
                    "metadata": {
                        "user_id": user_id,
                        "document_id": doc_id,
                        "document_name": filename,
                        "page": page_num,
                        "chunk_index": chunk_index
                    }
                })
                chunk_index += 1

            if end == text_len:
                break
            start += (chunk_size - overlap)

    return chunks

def index_document(user_id: int, doc_id: int, filename: str, pages_data: list):
    """
    Generates chunks and inserts them into ChromaDB.
    """
    chunks = chunk_text(pages_data, doc_id, user_id, filename)
    if not chunks:
        return 0

    ids = [c["id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    # Batch upsert to ChromaDB
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )
    return len(chunks)

def delete_document_from_index(user_id: int, doc_id: int):
    """
    Deletes all chunks belonging to a document.
    """
    try:
        collection.delete(
            where={
                "$and": [
                    {"user_id": user_id},
                    {"document_id": doc_id}
                ]
            }
        )
    except Exception as e:
        print(f"Error removing from vector store: {e}")

def query_rag(user_id: int, question: str, document_id: int = None, top_k: int = 4):
    """
    Retrieves top matching chunks with per-user isolation and answers strictly from context.
    """
    # Build filter
    if document_id:
        filter_expr = {
            "$and": [
                {"user_id": user_id},
                {"document_id": document_id}
            ]
        }
    else:
        filter_expr = {"user_id": user_id}

    results = collection.query(
        query_texts=[question],
        n_results=top_k,
        where=filter_expr
    )

    retrieved_docs = results.get("documents", [[]])[0]
    retrieved_metas = results.get("metadatas", [[]])[0]

    if not retrieved_docs:
        return {
            "answer": "I could not find any relevant information in your uploaded document(s) to answer this question.",
            "citations": []
        }

    # Format context for RAG
    context_blocks = []
    citations = []
    seen_sources = set()

    for doc_text, meta in zip(retrieved_docs, retrieved_metas):
        doc_name = meta.get("document_name", "Unknown")
        page = meta.get("page", 1)
        source_key = (doc_name, page)
        
        context_blocks.append(f"[Source: {doc_name}, Page {page}]\n{doc_text}")
        
        if source_key not in seen_sources:
            citations.append({
                "document_name": doc_name,
                "page": page,
                "snippet": doc_text[:180] + "..." if len(doc_text) > 180 else doc_text
            })
            seen_sources.add(source_key)

    context_str = "\n\n".join(context_blocks)

    # Attempt calling local Ollama if available
    llm_answer = None
    try:
        ollama_res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": f"""You are a helpful and strict Document QA Assistant.
Answer the user's question ONLY using the Context provided below.
If the answer is NOT present in the context, explicitly say:
"I could not find the answer to this question in the uploaded document(s)."

Context:
{context_str}

Question: {question}

Answer:""",
                "stream": False
            },
            timeout=8
        )
        if ollama_res.status_code == 200:
            llm_answer = ollama_res.json().get("response")
    except Exception:
        pass  # Ollama not running, fallback smoothly

    # Direct Synthesizer Fallback if Ollama isn't running
    if not llm_answer or not llm_answer.strip():
        # High quality extractive/synthesizing fallback from retrieved chunks
        q_words = set(re.findall(r'\w+', question.lower())) - {"what", "is", "the", "a", "an", "how", "why", "when", "where", "who", "which", "are", "can", "do", "does", "in", "of", "to", "for"}
        
        relevant_sentences = []
        for text in retrieved_docs:
            sentences = re.split(r'(?<=[.!?])\s+', text)
            for s in sentences:
                s_words = set(re.findall(r'\w+', s.lower()))
                overlap = len(q_words & s_words)
                if overlap > 0:
                    relevant_sentences.append((overlap, s.strip()))

        relevant_sentences.sort(key=lambda x: x[0], reverse=True)
        top_sentences = [s[1] for s in relevant_sentences[:4]]

        if top_sentences:
            llm_answer = " ".join(top_sentences)
        else:
            llm_answer = "Based on the retrieved context: " + retrieved_docs[0]

    return {
        "answer": llm_answer,
        "citations": citations
    }

def generate_summary(user_id: int, document_id: int):
    """
    Summarizes a document from its top chunks.
    """
    results = collection.get(
        where={
            "$and": [
                {"user_id": user_id},
                {"document_id": document_id}
            ]
        },
        limit=10
    )
    docs = results.get("documents", [])
    if not docs:
        return "No text available to summarize."

    sample_text = " ".join(docs[:4])
    # Extract first few key sentences
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', sample_text) if len(s.strip()) > 30]
    return " ".join(sentences[:5]) if sentences else sample_text[:600]
