import os
import sys

# Linux cloud deployment compatibility for ChromaDB (Render, AWS, Debian/Ubuntu)
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import re
import math
import time
import requests
from typing import Optional, Dict, Any, List
from collections import Counter
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

# Load environment variables from backend/.env
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(ENV_PATH)

# Azure OpenAI Configuration State loaded from .env
azure_config = {
    "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", "https://rag-42.openai.azure.com/openai/v1"),
    "api_key": os.getenv("AZURE_OPENAI_API_KEY", ""),
    "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or os.getenv("AZURE_OPENAI_MODEL", "gpt-5.6-luna"),
    "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
    "embedding_deployment": os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "")
}

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
os.makedirs(CHROMA_DIR, exist_ok=True)

client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = client.get_or_create_collection(name="dms_rag_collection")

# Common English stopwords for query keyword relevance filtering
STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "by", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "can", "could", "shall", "should", "will", "would", "may",
    "might", "must", "it", "its", "that", "this", "these", "those", "what", "which",
    "who", "whom", "whose", "where", "when", "why", "how", "as", "if", "than", "so"
}

def reload_env_config():
    """
    Reloads environment variables from .env into runtime state.
    """
    load_dotenv(ENV_PATH, override=True)
    azure_config["endpoint"] = os.getenv("AZURE_OPENAI_ENDPOINT", "https://rag-42.openai.azure.com/openai/v1")
    azure_config["api_key"] = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_config["deployment_name"] = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or os.getenv("AZURE_OPENAI_MODEL", "gpt-5.6-luna")
    azure_config["api_version"] = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
    azure_config["embedding_deployment"] = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "")

def get_azure_config() -> Dict[str, Any]:
    """
    Returns the current Azure OpenAI configuration with the API key partially masked.
    """
    reload_env_config()
    masked_key = ""
    if azure_config["api_key"]:
        key = azure_config["api_key"]
        masked_key = key[:4] + "••••••••" + key[-4:] if len(key) > 8 else "••••••••"

    return {
        "endpoint": azure_config["endpoint"],
        "deployment_name": azure_config["deployment_name"],
        "api_version": azure_config["api_version"],
        "is_configured": bool(azure_config["api_key"] and azure_config["endpoint"]),
        "masked_api_key": masked_key,
        "embedding_deployment": azure_config["embedding_deployment"]
    }

def update_azure_config(
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    deployment_name: Optional[str] = None,
    api_version: Optional[str] = None,
    embedding_deployment: Optional[str] = None
) -> Dict[str, Any]:
    """
    Updates the runtime Azure OpenAI configuration and persists changes to backend/.env.
    """
    if endpoint is not None:
        azure_config["endpoint"] = endpoint.strip()
    if api_key is not None and api_key.strip():
        azure_config["api_key"] = api_key.strip()
    if deployment_name is not None and deployment_name.strip():
        azure_config["deployment_name"] = deployment_name.strip()
    if api_version is not None and api_version.strip():
        azure_config["api_version"] = api_version.strip()
    if embedding_deployment is not None:
        azure_config["embedding_deployment"] = embedding_deployment.strip()

    # Persist to .env
    lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()

    env_map = {}
    for line in lines:
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.strip().split("=", 1)
            env_map[k] = v

    env_map["AZURE_OPENAI_ENDPOINT"] = azure_config["endpoint"]
    if azure_config["api_key"]:
        env_map["AZURE_OPENAI_API_KEY"] = azure_config["api_key"]
    env_map["AZURE_OPENAI_DEPLOYMENT_NAME"] = azure_config["deployment_name"]
    env_map["AZURE_OPENAI_MODEL"] = azure_config["deployment_name"]
    env_map["AZURE_OPENAI_API_VERSION"] = azure_config["api_version"]
    if azure_config["embedding_deployment"]:
        env_map["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"] = azure_config["embedding_deployment"]

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        for k, v in env_map.items():
            f.write(f"{k}={v}\n")

    return get_azure_config()

def normalize_azure_endpoint(endpoint: str) -> str:
    """
    Normalizes varied Azure OpenAI URLs into the standard base endpoint.
    E.g.: 'https://res.openai.azure.com/openai/v1' -> 'https://res.openai.azure.com'
    """
    ep = endpoint.strip().rstrip("/")
    match = re.match(r"(https?://[^/]+)", ep)
    if match:
        return match.group(1)
    return ep

def split_into_sentences(text: str) -> list:
    """
    Splits text into clean, distinct sentences while preserving honorifics and abbreviations.
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
            if raw_text.strip():
                words = raw_text.split()
                step = 100
                for i in range(0, len(words), step):
                    chunk_body = " ".join(words[i:i + step + 25])
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
            if len(chunk_body) > 15:
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

def call_azure_openai(
    system_prompt: str,
    user_prompt: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
    max_tokens: int = 1500,
    temperature: float = 0.2
) -> Optional[str]:
    """
    Sends request to Azure OpenAI GPT deployment using both the official openai.AzureOpenAI SDK
    and direct REST API fallback for maximum compatibility.
    Adaptive to both reasoning models (gpt-5.6-luna / o-series with max_completion_tokens)
    and standard models (gpt-4o, gpt-4 with max_tokens).
    """
    reload_env_config()
    api_key = azure_config.get("api_key")
    raw_endpoint = azure_config.get("endpoint", "")
    deployment_name = azure_config.get("deployment_name", "gpt-5.6-luna")
    api_version = azure_config.get("api_version", "2024-08-01-preview")

    if not api_key or not raw_endpoint:
        return None

    base_endpoint = normalize_azure_endpoint(raw_endpoint)

    # Build messages array
    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        for turn in chat_history[-3:]:
            q = turn.get("question")
            a = turn.get("answer")
            if q and a:
                messages.append({"role": "user", "content": q})
                messages.append({"role": "assistant", "content": a})
    messages.append({"role": "user", "content": user_prompt})

    # 1. Primary: Official AzureOpenAI client from openai package
    try:
        from openai import AzureOpenAI
        client_aoai = AzureOpenAI(
            azure_endpoint=base_endpoint,
            api_key=api_key,
            api_version=api_version,
            timeout=40.0
        )
        try:
            # Try max_completion_tokens first (required for gpt-5.6-luna and reasoning models)
            response = client_aoai.chat.completions.create(
                model=deployment_name,
                messages=messages,
                max_completion_tokens=max_tokens
            )
        except Exception as e_comp:
            # Fallback to max_tokens + temperature for standard models (gpt-4o, etc.)
            response = client_aoai.chat.completions.create(
                model=deployment_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
        content = response.choices[0].message.content
        if content:
            return content.strip()
    except Exception as sdk_err:
        print(f"[AzureOpenAI SDK] Call failed: {sdk_err}. Trying direct REST fallback...")

    # 2. Fallback: Direct Azure OpenAI REST API call
    rest_url = f"{base_endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json"
    }

    # Try max_completion_tokens
    payload1 = {
        "messages": messages,
        "max_completion_tokens": max_tokens
    }
    try:
        res = requests.post(rest_url, headers=headers, json=payload1, timeout=40)
        if res.status_code == 200:
            data = res.json()
            return data["choices"][0]["message"]["content"].strip()
        elif "max_tokens" in res.text:
            payload2 = {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            res2 = requests.post(rest_url, headers=headers, json=payload2, timeout=40)
            if res2.status_code == 200:
                data2 = res2.json()
                return data2["choices"][0]["message"]["content"].strip()
    except Exception as rest_err:
        print(f"[AzureOpenAI REST] Failed: {rest_err}")

    # 3. Third variant: If user provided endpoint ending in /openai/v1
    if "/v1" in raw_endpoint:
        alt_url = f"{raw_endpoint.rstrip('/')}/chat/completions"
        payload_alt = {
            "model": deployment_name,
            "messages": messages,
            "max_completion_tokens": max_tokens
        }
        try:
            res_alt = requests.post(alt_url, headers=headers, json=payload_alt, timeout=40)
            if res_alt.status_code == 200:
                data = res_alt.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

    return None

def test_azure_openai_connection(
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    deployment_name: Optional[str] = None,
    api_version: Optional[str] = None
) -> Dict[str, Any]:
    """
    Tests live connectivity to an Azure OpenAI GPT deployment.
    """
    reload_env_config()
    target_endpoint = normalize_azure_endpoint(endpoint or azure_config["endpoint"])
    target_key = api_key or azure_config["api_key"]
    target_deployment = deployment_name or azure_config["deployment_name"]
    target_version = api_version or azure_config["api_version"]

    if not target_endpoint or not target_key or not target_deployment:
        return {
            "success": False,
            "error": "Missing required fields: Endpoint, API Key, and Deployment Name must all be provided."
        }

    start_time = time.time()

    # Try official SDK first
    try:
        from openai import AzureOpenAI
        client_aoai = AzureOpenAI(
            azure_endpoint=target_endpoint,
            api_key=target_key,
            api_version=target_version,
            timeout=20.0
        )
        try:
            response = client_aoai.chat.completions.create(
                model=target_deployment,
                messages=[
                    {"role": "user", "content": "Respond with 'CONNECTION_SUCCESSFUL'."}
                ],
                max_completion_tokens=25
            )
        except Exception:
            response = client_aoai.chat.completions.create(
                model=target_deployment,
                messages=[
                    {"role": "user", "content": "Respond with 'CONNECTION_SUCCESSFUL'."}
                ],
                max_tokens=25
            )

        latency = round((time.time() - start_time) * 1000)
        reply = response.choices[0].message.content.strip()
        return {
            "success": True,
            "message": f"Successfully connected to Azure OpenAI deployment '{target_deployment}'!",
            "latency_ms": latency,
            "deployment": target_deployment,
            "response_preview": reply
        }
    except Exception as err:
        error_msg = str(err)
        # Attempt REST API test to get clearer HTTP status
        try:
            url = f"{target_endpoint}/openai/deployments/{target_deployment}/chat/completions?api-version={target_version}"
            res = requests.post(
                url,
                headers={"api-key": target_key, "Content-Type": "application/json"},
                json={
                    "messages": [{"role": "user", "content": "Respond with 'CONNECTION_SUCCESSFUL'."}],
                    "max_completion_tokens": 25
                },
                timeout=20
            )
            latency = round((time.time() - start_time) * 1000)
            if res.status_code == 200:
                return {
                    "success": True,
                    "message": f"Successfully connected to Azure OpenAI deployment '{target_deployment}' via REST API!",
                    "latency_ms": latency,
                    "deployment": target_deployment
                }
            else:
                return {
                    "success": False,
                    "error": f"Azure OpenAI responded with HTTP {res.status_code}: {res.text}",
                    "status_code": res.status_code
                }
        except Exception as rest_err:
            return {
                "success": False,
                "error": f"Connection failed: {error_msg} (REST check: {str(rest_err)})"
            }

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

def query_rag(user_id: int, question: str, document_id: int = None, chat_history: list = None, top_k: int = 6):
    """
    Retrieves matching document chunks from ChromaDB and uses the Azure OpenAI GPT model
    to answer questions accurately with source citations.
    """
    clean_q = question.strip()
    q_tokens = [w for w in re.findall(r'\b\w+\b', clean_q.lower()) if w not in STOPWORDS]

    # Filter expression for user & optional doc isolation
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
            "citations": [],
            "model_used": "Error"
        }

    retrieved_docs = results.get("documents", [[]])[0]
    retrieved_metas = results.get("metadatas", [[]])[0]

    if not retrieved_docs:
        return {
            "answer": "I could not find any relevant information in your uploaded document(s) to answer this question. Please make sure the document has been processed and indexed.",
            "citations": [],
            "model_used": "Vector Store"
        }

    # Relevance check: if question has 0 keyword overlap with any retrieved chunk
    combined_docs_text = " ".join(retrieved_docs).lower()
    matched_query_tokens = [t for t in q_tokens if t in combined_docs_text]

    if len(q_tokens) >= 2 and len(matched_query_tokens) == 0:
        return {
            "answer": "I could not find the answer to this question in the uploaded document(s).",
            "citations": [],
            "model_used": "Context Filter"
        }

    # Build structured context & extract citations
    context_blocks = []
    citations = []
    seen_sources = set()

    for doc_text, meta in zip(retrieved_docs, retrieved_metas):
        doc_name = meta.get("document_name", "Unknown Document")
        page = meta.get("page", 1)
        source_key = (doc_name, page)

        context_blocks.append(f"[Document: {doc_name} | Page {page}]\n{doc_text}")

        if source_key not in seen_sources and len(citations) < 5:
            snippet = doc_text[:220] + "..." if len(doc_text) > 220 else doc_text
            citations.append({
                "document_name": doc_name,
                "page": page,
                "snippet": snippet
            })
            seen_sources.add(source_key)

    context_str = "\n\n---\n\n".join(context_blocks)

    # System prompt for Azure OpenAI GPT model
    deployment_label = azure_config.get("deployment_name", "gpt-5.6-luna")
    system_prompt = (
        f"You are an intelligent Document Assistant powered by Azure OpenAI ({deployment_label}).\n"
        "Your task is to answer user questions with high precision, strictly based on the provided document excerpts below.\n\n"
        "Rules:\n"
        "1. Base your answer ONLY on the facts present in the Context. Do not invent facts or extrapolate beyond what is documented.\n"
        "2. If the context contains sufficient information, provide a thorough, clear, and well-structured answer using Markdown (bullet points, bold highlights, concise paragraphs).\n"
        "3. When stating key facts, cite the source document name and page number (e.g., '[Document: example.pdf, Page 2]').\n"
        "4. If the context answers only part of the question, answer that part and explicitly state what part could not be found.\n"
        "5. ONLY if the Context contains NO relevant information at all, state clearly: "
        "'I could not find the answer to this question in the uploaded document(s).'"
    )

    user_prompt = f"Document Context:\n{context_str}\n\nQuestion: {clean_q}\n\nAnswer:"

    llm_answer = call_azure_openai(system_prompt, user_prompt, chat_history=chat_history)
    model_name = f"{deployment_label} (Azure OpenAI)" if llm_answer else "Local Extraction Engine"

    # Local fallback if Azure OpenAI is unconfigured or unreachable
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
                if len(top_evidence) >= 4:
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
    Summarizes document content using the configured Azure OpenAI GPT model.
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

    sample_context = "\n\n".join(docs[:8])

    deployment_label = azure_config.get("deployment_name", "gpt-5.6-luna")
    system_prompt = (
        f"You are an executive document analyst powered by Azure OpenAI ({deployment_label}).\n"
        "Generate a structured, concise executive summary of the document excerpt provided below.\n"
        "Format with:\n"
        "- **Core Objective / Overview** (1-2 sentences)\n"
        "- **Key Highlights & Takeaways** (3-5 bullet points)\n"
        "- **Important Notes, Requirements, or Metrics**"
    )
    user_prompt = f"Document excerpt:\n{sample_context}\n\nPlease generate a clear executive summary:"

    llm_summary = call_azure_openai(system_prompt, user_prompt, max_tokens=800)
    if llm_summary:
        return llm_summary

    # Fallback summary
    summary_sentences = []
    seen = set()
    for d in docs[:6]:
        for s in split_into_sentences(d):
            if len(s) > 35 and s not in seen:
                summary_sentences.append(s)
                seen.add(s)
                break
    return " ".join(summary_sentences[:5]) if summary_sentences else docs[0][:600]
