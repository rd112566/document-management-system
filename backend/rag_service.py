import os
import re
import math
from collections import Counter
import chromadb
import requests

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
os.makedirs(CHROMA_DIR, exist_ok=True)

client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = client.get_or_create_collection(name="dms_rag_collection")

# Stopwords to filter out during keyword scoring
STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "by", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "can", "could", "shall", "should", "will", "would", "may",
    "might", "must", "it", "its", "that", "this", "these", "those", "what", "which",
    "who", "whom", "whose", "where", "when", "why", "how", "as", "if", "than", "so"
}

def split_into_sentences(text: str) -> list:
    """
    Splits text into clean, distinct sentences.
    """
    # Protect common abbreviations
    text = re.sub(r'\b(Dr|Mr|Mrs|Ms|Prof|vs|Inc|Ltd|e\.g|i\.e)\.', r'\1<DOT>', text)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    cleaned = []
    for s in sentences:
        s = s.replace('<DOT>', '.').strip()
        if len(s) > 10:
            cleaned.append(s)
    return cleaned

def chunk_text(pages_data, doc_id: int, user_id: int, filename: str, target_size: int = 700, overlap_size: int = 150):
    """
    Sentence-aware chunking preserving whole sentences, context, and page numbers.
    """
    chunks = []
    chunk_index = 0

    for page_item in pages_data:
        page_num = page_item["page"]
        raw_text = page_item["text"]

        sentences = split_into_sentences(raw_text)
        if not sentences:
            continue

        current_sentences = []
        current_len = 0

        for s in sentences:
            s_len = len(s)
            if current_len + s_len > target_size and current_sentences:
                chunk_body = " ".join(current_sentences)
                chunks.append({
                    "id": f"user_{user_id}_doc_{doc_id}_chunk_{chunk_index}",
                    "text": chunk_body,
                    "metadata": {
                        "user_id": user_id,
                        "document_id": doc_id,
                        "document_name": filename,
                        "page": page_num,
                        "chunk_index": chunk_index
                    }
                })
                chunk_index += 1

                # Sliding overlap: keep last sentence(s) that fit in overlap_size
                overlap_sentences = []
                overlap_len = 0
                for prev_s in reversed(current_sentences):
                    if overlap_len + len(prev_s) <= overlap_size:
                        overlap_sentences.insert(0, prev_s)
                        overlap_len += len(prev_s)
                    else:
                        break
                current_sentences = overlap_sentences
                current_len = overlap_len

            current_sentences.append(s)
            current_len += s_len

        # Remaining sentences on page
        if current_sentences:
            chunk_body = " ".join(current_sentences)
            if len(chunk_body) > 20:
                chunks.append({
                    "id": f"user_{user_id}_doc_{doc_id}_chunk_{chunk_index}",
                    "text": chunk_body,
                    "metadata": {
                        "user_id": user_id,
                        "document_id": doc_id,
                        "document_name": filename,
                        "page": page_num,
                        "chunk_index": chunk_index
                    }
                })
                chunk_index += 1

    return chunks

def index_document(user_id: int, doc_id: int, filename: str, pages_data: list):
    """
    Chunks document content and writes vectors into ChromaDB.
    """
    chunks = chunk_text(pages_data, doc_id, user_id, filename)
    if not chunks:
        return 0

    ids = [c["id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    # Insert in batches of 100 to prevent payload limits
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        collection.upsert(
            ids=ids[i:i + batch_size],
            documents=documents[i:i + batch_size],
            metadatas=metadatas[i:i + batch_size]
        )
    return len(chunks)

def delete_document_from_index(user_id: int, doc_id: int):
    """
    Deletes all vector embeddings associated with this document.
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

def score_sentence_relevance(sentence: str, query_tokens: list, query_lower: str) -> float:
    """
    Scores how well an individual sentence answers the query based on token overlap,
    exact phrase matches, numbers, and capitalizations.
    """
    s_lower = sentence.lower()
    score = 0.0

    # Exact phrase matches
    if len(query_lower) > 5 and query_lower in s_lower:
        score += 5.0

    # Token overlap with bonus for uncommon words
    for token in query_tokens:
        if token in s_lower:
            # Word length weighting (longer words like "superposition" carry more meaning)
            score += 1.0 + (len(token) * 0.15)

    # Question-specific heuristics
    # Numbers/Dates
    if any(q_word in query_lower for q_word in ["when", "year", "date", "how many", "how much", "number"]):
        if re.search(r'\b\d+(?:[\.,]\d+)?\b', sentence):
            score += 2.5

    # Entity/Names
    if any(q_word in query_lower for q_word in ["who", "which company", "which processor", "what processor"]):
        if re.search(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', sentence):
            score += 2.0

    return score

def query_rag(user_id: int, question: str, document_id: int = None, top_k: int = 6):
    """
    Retrieves top matching chunks with per-user isolation, executes strict context verification,
    and returns high-accuracy answers with page citations.
    """
    clean_q = question.strip()
    q_tokens = [w for w in re.findall(r'\b\w+\b', clean_q.lower()) if w not in STOPWORDS]

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

    # Query ChromaDB
    try:
        results = collection.query(
            query_texts=[clean_q],
            n_results=top_k,
            where=filter_expr
        )
    except Exception as e:
        print(f"ChromaDB query error: {e}")
        return {
            "answer": "Could not access vector index. Please ensure the document is uploaded.",
            "citations": []
        }

    retrieved_docs = results.get("documents", [[]])[0]
    retrieved_metas = results.get("metadatas", [[]])[0]

    if not retrieved_docs:
        return {
            "answer": "I could not find any relevant information in your uploaded document(s) to answer this question.",
            "citations": []
        }

    # 1. Verification of relevance
    # Check total keyword overlap between query and all retrieved documents
    combined_docs_text = " ".join(retrieved_docs).lower()
    matched_query_tokens = [t for t in q_tokens if t in combined_docs_text]

    # If the user asks a completely unrelated question (e.g. "Who is the President of Mars?"), reject cleanly
    if len(q_tokens) >= 2 and len(matched_query_tokens) == 0:
        return {
            "answer": "I could not find the answer to this question in the uploaded document(s).",
            "citations": []
        }

    # 2. Extract citations & format context
    citations = []
    seen_sources = set()

    # Score sentences across retrieved chunks
    scored_sentences = []
    for doc_text, meta in zip(retrieved_docs, retrieved_metas):
        doc_name = meta.get("document_name", "Unknown Document")
        page = meta.get("page", 1)
        source_key = (doc_name, page)

        sentences = split_into_sentences(doc_text)
        for s in sentences:
            score = score_sentence_relevance(s, q_tokens, clean_q.lower())
            if score > 0:
                scored_sentences.append({
                    "score": score,
                    "sentence": s,
                    "document_name": doc_name,
                    "page": page
                })

        if source_key not in seen_sources and len(citations) < 4:
            snippet = doc_text[:200] + "..." if len(doc_text) > 200 else doc_text
            citations.append({
                "document_name": doc_name,
                "page": page,
                "snippet": snippet
            })
            seen_sources.add(source_key)

    # 3. Check for external LLM (Ollama or Groq/OpenAI/Gemini API)
    llm_answer = None

    # Try local Ollama if running
    try:
        ollama_res = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": f"""You are a helpful, precise RAG Document QA assistant.
Answer the question directly and concisely based ONLY on the provided Context.
If the answer is NOT stated in the context, say: "I could not find the answer to this question in the uploaded document(s)."

Context:
{" ".join(retrieved_docs[:4])}

Question: {clean_q}

Answer:""",
                "stream": False
            },
            timeout=5
        )
        if ollama_res.status_code == 200:
            resp_text = ollama_res.json().get("response", "").strip()
            if resp_text:
                llm_answer = resp_text
    except Exception:
        pass

    # 4. If no external LLM, use the High-Accuracy Cognitive Synthesizer
    if not llm_answer:
        scored_sentences.sort(key=lambda x: x["score"], reverse=True)

        if scored_sentences and scored_sentences[0]["score"] >= 1.0:
            # Pick top 2-3 most coherent evidence sentences
            top_evidence = []
            seen_text = set()
            for item in scored_sentences:
                s_text = item["sentence"]
                if s_text not in seen_text:
                    top_evidence.append(s_text)
                    seen_text.add(s_text)
                if len(top_evidence) >= 3:
                    break

            llm_answer = " ".join(top_evidence)
        else:
            # Direct first chunk fallback
            llm_answer = retrieved_docs[0]

    return {
        "answer": llm_answer,
        "citations": citations
    }

def generate_summary(user_id: int, document_id: int):
    """
    Summarizes document content from representative page chunks.
    """
    results = collection.get(
        where={
            "$and": [
                {"user_id": user_id},
                {"document_id": document_id}
            ]
        },
        limit=12
    )
    docs = results.get("documents", [])
    if not docs:
        return "No text available to summarize."

    # Extract leading sentences across chunks
    summary_sentences = []
    seen = set()
    for d in docs[:6]:
        sentences = split_into_sentences(d)
        for s in sentences:
            if len(s) > 35 and s not in seen:
                summary_sentences.append(s)
                seen.add(s)
                break

    if summary_sentences:
        return " ".join(summary_sentences[:5])
    return docs[0][:500]
