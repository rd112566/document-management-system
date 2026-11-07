import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(__file__))

from database import get_db_connection, init_db
from rag_service import query_rag, generate_summary, azure_config
from ingest_samples import ingest_all_samples

EVALUATION_QUESTIONS = [
    {
        "id": 1,
        "question": "What did Google Quantum AI demonstrate in 2019?",
        "expected_keywords": ["sycamore", "53-qubit", "supremacy"],
        "expected_doc": "quantum_computing_overview.pdf",
        "expected_page": 1,
        "type": "fact"
    },
    {
        "id": 2,
        "question": "What speedup does Grover's algorithm provide?",
        "expected_keywords": ["quadratic", "database"],
        "expected_doc": "quantum_computing_overview.pdf",
        "expected_page": 2,
        "type": "fact"
    },
    {
        "id": 3,
        "question": "What algorithm can factor large integers exponentially faster?",
        "expected_keywords": ["shor"],
        "expected_doc": "quantum_computing_overview.pdf",
        "expected_page": 2,
        "type": "fact"
    },
    {
        "id": 4,
        "question": "How many physical qubits are needed per logical qubit in fault-tolerant computing?",
        "expected_keywords": ["thousands", "physical"],
        "expected_doc": "quantum_computing_overview.pdf",
        "expected_page": 2,
        "type": "fact"
    },
    {
        "id": 5,
        "question": "What encryption standard is required by the AI policy?",
        "expected_keywords": ["aes-256"],
        "expected_doc": "sample_ai_policy.txt",
        "expected_page": 1,
        "type": "fact"
    },
    {
        "id": 6,
        "question": "How long can authentication tokens last before expiring?",
        "expected_keywords": ["24 hours", "24"],
        "expected_doc": "sample_ai_policy.txt",
        "expected_page": 1,
        "type": "fact"
    },
    {
        "id": 7,
        "question": "Does the AI policy allow User A to see User B's documents?",
        "expected_keywords": ["no", "never", "isolation"],
        "expected_doc": "sample_ai_policy.txt",
        "expected_page": 1,
        "type": "fact"
    },
    {
        "id": 8,
        "question": "What must accompany every factual statement in RAG answers according to the policy?",
        "expected_keywords": ["page", "document", "source"],
        "expected_doc": "sample_ai_policy.txt",
        "expected_page": 1,
        "type": "fact"
    },
    {
        "id": 9,
        "question": "What is the project budget specified in the requirements?",
        "expected_keywords": ["open-source"],
        "expected_doc": "project_requirements.docx",
        "expected_page": 1,
        "type": "fact"
    },
    {
        "id": 10,
        "question": "What file formats must the document extraction support?",
        "expected_keywords": ["pdf", "docx"],
        "expected_doc": "project_requirements.docx",
        "expected_page": 1,
        "type": "fact"
    },
    {
        "id": 11,
        "question": "What vector store is specified in the requirements?",
        "expected_keywords": ["chromadb"],
        "expected_doc": "project_requirements.docx",
        "expected_page": 1,
        "type": "fact"
    },
    {
        "id": 12,
        "question": "What is the deadline mentioned in the project specification?",
        "expected_keywords": ["november 2026"],
        "expected_doc": "project_requirements.docx",
        "expected_page": 1,
        "type": "fact"
    },
    {
        "id": 13,
        "question": "What is a qubit's superposition state?",
        "expected_keywords": ["linear combination"],
        "expected_doc": "quantum_computing_overview.pdf",
        "expected_page": 1,
        "type": "fact"
    },
    {
        "id": 14,
        "question": "What type of codes are required for quantum error correction?",
        "expected_keywords": ["surface codes", "surface"],
        "expected_doc": "quantum_computing_overview.pdf",
        "expected_page": 2,
        "type": "fact"
    },
    {
        "id": 15,
        "question": "What should the system say if an answer is not in the documents?",
        "expected_keywords": ["not found", "not present"],
        "expected_doc": "sample_ai_policy.txt",
        "expected_page": 1,
        "type": "fact"
    },
    {
        "id": 16,
        "question": "Who is the President of Mars?",
        "expected_keywords": ["not find", "not found", "no information"],
        "type": "negative"
    },
    {
        "id": 17,
        "question": "What is the recipe for chocolate cake?",
        "expected_keywords": ["not find", "not found", "no information"],
        "type": "negative"
    },
    {
        "id": 18,
        "question": "What are the three main deliverables of the project?",
        "expected_keywords": ["extraction", "chunking", "qa", "deliverables"],
        "expected_doc": "project_requirements.docx",
        "expected_page": 1,
        "type": "fact"
    },
    {
        "id": 19,
        "question": "What was the revenue and net profit reported for Q2 2026?",
        "expected_keywords": ["1,480,000", "410,000"],
        "expected_doc": "quarterly_financials.csv",
        "expected_page": 1,
        "type": "fact"
    },
    {
        "id": 20,
        "question": "Which cloud resource runs Azure OpenAI Service in East US?",
        "expected_keywords": ["vm-ai-rag-01", "east us"],
        "expected_doc": "cloud_infrastructure_inventory.xlsx",
        "expected_page": 1,
        "type": "fact"
    }
]

def run_benchmark(user_id: int = 1):
    print("=" * 70)
    print("  Intelligent Document Management System - Benchmark Suite")
    print(f"  Target LLM: {azure_config.get('deployment_name')} (Azure OpenAI)")
    print(f"  Endpoint:   {azure_config.get('endpoint')}")
    print("=" * 70)

    # Ingest samples
    print("\n[Step 1] Ensuring sample documents are ingested...")
    ingest_all_samples(user_id=user_id)

    print("\n[Step 2] Executing 20 Evaluation Benchmark Questions...\n")
    passed = 0
    total = len(EVALUATION_QUESTIONS)

    results = []

    for item in EVALUATION_QUESTIONS:
        q_id = item["id"]
        q_text = item["question"]
        q_type = item["type"]

        print(f"Q{q_id:02d}: {q_text}")
        start_t = time.time()
        res = query_rag(user_id=user_id, question=q_text, top_k=6)
        elapsed = round(time.time() - start_t, 2)

        ans = res.get("answer", "")
        citations = res.get("citations", [])
        model_used = res.get("model_used", "")

        ans_lower = ans.lower()

        # Check keywords
        has_keywords = any(kw.lower() in ans_lower for kw in item["expected_keywords"])

        # Check citations if fact question
        has_citation = True
        if q_type == "fact" and "expected_doc" in item:
            has_citation = any(
                item["expected_doc"].lower() in c.get("document_name", "").lower()
                for c in citations
            )

        is_pass = has_keywords and (has_citation or q_type == "negative")
        if is_pass:
            passed += 1
            status_str = "✅ PASS"
        else:
            status_str = "❌ FAIL"

        results.append({
            "id": q_id,
            "status": status_str,
            "latency": f"{elapsed}s",
            "model": model_used,
            "answer_preview": (ans[:90] + "...") if len(ans) > 90 else ans
        })

        print(f"     Status: {status_str} ({elapsed}s, model: {model_used})")
        print(f"     Answer: {ans[:100]}...\n")

    print("=" * 70)
    print(f"  BENCHMARK SUMMARY: {passed}/{total} Passed ({round(passed / total * 100, 1)}%)")
    print("=" * 70)

    return passed == total

if __name__ == "__main__":
    init_db()
    run_benchmark(user_id=1)
