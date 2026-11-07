import os
import re
import math
from collections import Counter
import chromadb
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://rag-42.openai.azure.com/openai/v1")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL", "gpt-5.6-luna")

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

def call_azure_openai(system_prompt: str, user_prompt: str) -> str:
    """
    Sends request to Azure OpenAI gpt-5.6-luna endpoint.
    """
    if not AZURE_OPENAI_API_KEY:
        return None

    url = f"{AZURE_OPENAI_ENDPOINT.rstrip('/')}/chat/completions"
    headers = {
        "api-key": AZURE_OPENAI_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "model": AZURE_OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        if res.status_code == 200:
            data = res.json()
            return data["choices"][0]["message"]["content"].strip()
        else:
            print(f"Azure OpenAI Error ({res.status_code}): {res.text}")
    except Exception as err:
        print(f"Azure OpenAI call failed: {err}")
    return None

def score_sentence_relevance(sentence: str, query_tokens: list, query_lower: str) -> float:
    """
    Scores how well an individual sentence answers the query.
    """
    s_lower = sentence.lower()
    score = 0.0

    if len(query_lower) > 5 and query_lower in s_lower:
        score += 5.0

    for token in query_tokens:
        if token in s_lower:
            score += 1.0 + (len(token) * 0.15)

    if any(q_word in query_lower for q_word in ["when", "year", "date", "how many", "how much", "number"]):
        if re.search(r'\b\d+(?:[\.,]\d+)?\b', sentence):
            score += 2.5

    if any(q_word in query_lower for q_word in ["who", "which company", "which processor", "what processor"]):
        if re.search(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', sentence):
            score += 2.0

    return score

def query_rag(user_id: int, question: str, document_id: int = None, top_k: int = 6):
    """
    Retrieves top matching chunks with per-user isolation, executes Azure OpenAI (gpt-5.6-luna) reasoning,
    and returns high-accuracy answers with page citations.
    """
    clean_q = question.strip()
    q_tokens = [w for w in re.findall(r'\b\w+\b', clean_q.lower()) if w not in STOPWORDS]

    # Filter expression for user & doc isolation
    if document_id:
        filter_expr = {
            "$and": [
                {"user_id": user_id},
                {"document_id": document_id}
            ]
        }
    else:
        filter_expr = {"user_id": user_id}

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

    # Relevance check: if question has 0 keyword overlap with any retrieved chunk
    combined_docs_text = " ".join(retrieved_docs).lower()
    matched_query_tokens = [t for t in q_tokens if t in combined_docs_text]

    if len(q_tokens) >= 2 and len(matched_query_tokens) == 0:
        return {
            "answer": "I could not find the answer to this question in the uploaded document(s).",
            "citations": []
        }

    # Build structured context & extract citations
    context_blocks = []
    citations = []
    seen_sources = set()

    for doc_text, meta in zip(retrieved_docs, retrieved_metas):
        doc_name = meta.get("document_name", "Unknown Document")
        page = meta.get("page", 1)
        source_key = (doc_name, page)

        context_blocks.append(f"[Source: {doc_name} | Page {page}]\n{doc_text}")

        if source_key not in seen_sources and len(citations) < 4:
            snippet = doc_text[:200] + "..." if len(doc_text) > 200 else doc_text
            citations.append({
                "document_name": doc_name,
                "page": page,
                "snippet": snippet
            })
            seen_sources.add(source_key)

    context_str = "\n\n".join(context_blocks)

    # 1. Ask Azure OpenAI (gpt-5.6-luna)
    system_prompt = (
        "You are an expert Document QA Assistant operating inside a Retrieval-Augmented Generation (RAG) system.\n"
        "Instructions:\n"
        "1. Answer the question thoroughly, clearly, and accurately based on the provided Context below.\n"
        "2. If the question asks about multiple aspects (e.g., both advantages and disadvantages, or multiple topics) and only some aspects are present in the Context, provide all the information that IS available from the Context, and briefly note which specific sub-parts are not mentioned.\n"
        "3. ONLY if the Context contains NO relevant information at all to answer the user's question, reply with: "
        "'I could not find the answer to this question in the uploaded document(s).'\n"
        "4. Format your response cleanly using Markdown (headers, bullet points).\n"
        "5. Cite the source document name and page numbers for the facts you present."
    )

    user_prompt = f"Context:\n{context_str}\n\nQuestion: {clean_q}\n\nAnswer:"

    llm_answer = call_azure_openai(system_prompt, user_prompt)
    model_name = f"{AZURE_OPENAI_MODEL} (Azure OpenAI)" if llm_answer else "Local Fallback Engine"

    if llm_answer:
        print(f"[RAG Engine] Successfully answered using {model_name}")

    # 2. Local Fallback if Azure OpenAI is unreachable
    if not llm_answer:
        scored_sentences = []
        for doc_text, meta in zip(retrieved_docs, retrieved_metas):
            for s in split_into_sentences(doc_text):
                score = score_sentence_relevance(s, q_tokens, clean_q.lower())
                if score > 0:
                    scored_sentences.append({"score": score, "sentence": s})

        scored_sentences.sort(key=lambda x: x["score"], reverse=True)
        if scored_sentences and scored_sentences[0]["score"] >= 1.0:
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
            llm_answer = retrieved_docs[0]

    return {
        "answer": llm_answer,
        "citations": citations,
        "model_used": model_name
    }

def generate_summary(user_id: int, document_id: int):
    """
    Summarizes document content using Azure OpenAI gpt-5.6-luna.
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

    sample_context = "\n\n".join(docs[:6])

    system_prompt = (
        "You are an executive document analyst. Write a concise, structured executive summary (3-5 bullet points) "
        "highlighting the core objectives, key findings, and important details of the provided document."
    )
    user_prompt = f"Document excerpt:\n{sample_context}\n\nPlease generate a clear executive summary:"

    llm_summary = call_azure_openai(system_prompt, user_prompt)
    if llm_summary:
        return llm_summary

    # Fallback summary
    summary_sentences = []
    seen = set()
    for d in docs[:5]:
        for s in split_into_sentences(d):
            if len(s) > 35 and s not in seen:
                summary_sentences.append(s)
                seen.add(s)
                break
    return " ".join(summary_sentences[:4]) if summary_sentences else docs[0][:500]
