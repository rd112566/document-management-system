# DocuMind RAG — Prompt Engineering & Evaluation Documentation

This document outlines the complete prompt engineering catalog, system prompts, retrieval instructions, conversational memory structures, and the 20-question benchmark evaluation suite implemented in the **Intelligent Document Management System with Azure OpenAI RAG**.

---

## 📑 Table of Contents

1. [Architectural Overview & Prompt Flow](#1-architectural-overview--prompt-flow)
2. [Production System Prompts](#2-production-system-prompts)
   - [2.1 Grounded Document QA Prompt (Azure OpenAI GPT)](#21-grounded-document-qa-prompt-azure-openai-gpt)
   - [2.2 Executive Document Summarization Prompt](#22-executive-document-summarization-prompt)
   - [2.3 Azure OpenAI Connectivity Ping Prompt](#23-azure-openai-connectivity-ping-prompt)
   - [2.4 Local Extraction & Fallback Heuristic](#24-local-extraction--fallback-heuristic)
3. [Multi-Turn Conversational Memory Prompting](#3-multi-turn-conversational-memory-prompting)
4. [20 Evaluation Benchmark Prompts](#4-20-evaluation-benchmark-prompts)
   - [Fact Retrieval Prompts (Q1 - Q15, Q18 - Q20)](#fact-retrieval-prompts)
   - [Negative Constraint & Anti-Hallucination Prompts (Q16 - Q17)](#negative-constraint--anti-hallucination-prompts)
5. [Prompt Engineering Best Practices for Azure OpenAI](#5-prompt-engineering-best-practices-for-azure-openai)

---

## 1. Architectural Overview & Prompt Flow

The Document Management System follows a strict, grounded Retrieval-Augmented Generation (RAG) architecture:

```
[User Document Upload (PDF, DOCX, XLSX, CSV, JSON, TXT)]
           │
           ▼
[Text Extraction & Page-Aware Sentence Chunking (extractor.py)]
           │
           ▼
[Vector Embedding & Persistent Indexing (ChromaDB)]
           │
           ▼
[User Question Input] ─────────► [Semantic Vector Query (top_k=6 chunks)]
                                           │
                                           ▼
                            [Context Assembly & Citation Linking]
                            [Source: filename.pdf | Page X]
                                           │
                                           ▼
[Multi-turn History (Last 3 Turns)] ──► [System Prompt + User Prompt]
                                           │
                                           ▼
             [Azure OpenAI GPT Deployment: gpt-5.6-luna / gpt-4o]
             (Adaptive max_completion_tokens / temperature=0.2)
                                           │
                                           ▼
             [Grounded Answer with Page Citations & Fallback Safety]
```

---

## 2. Production System Prompts

### 2.1 Grounded Document QA Prompt (Azure OpenAI GPT)

Located in [`backend/rag_service.py`](file:///d:/document-management-system/backend/rag_service.py):

#### System Prompt:
```text
You are an intelligent Document Assistant powered by Azure OpenAI ({deployment_label}).
Your task is to answer user questions with high precision, strictly based on the provided document excerpts below.

Rules:
1. Base your answer ONLY on the facts present in the Context. Do not invent facts or extrapolate beyond what is documented.
2. If the context contains sufficient information, provide a thorough, clear, and well-structured answer using Markdown (bullet points, bold highlights, concise paragraphs).
3. When stating key facts, cite the source document name and page number (e.g., '[Document: example.pdf, Page 2]').
4. If the context answers only part of the question, answer that part and explicitly state what part could not be found.
5. ONLY if the Context contains NO relevant information at all, state clearly:
   'I could not find the answer to this question in the uploaded document(s).'
```

#### User Prompt Template:
```text
Document Context:
[Document: {doc_name} | Page {page_number}]
{extracted_chunk_text_1}

---

[Document: {doc_name} | Page {page_number}]
{extracted_chunk_text_2}

Question: {user_question}

Answer:
```

#### Key Design Rationales:
- **Strict Grounding Rule**: Restricts knowledge retrieval exclusively to provided context, preventing hallucinations.
- **Synthesized Citations**: Forces the model to annotate facts with `[Document: filename, Page X]`, which the React frontend parses and highlights as interactive badges.
- **Partial Answering**: Rather than failing entirely on multi-part queries, the model supplies the known sub-parts and transparently flags missing information.

---

### 2.2 Executive Document Summarization Prompt

Located in [`backend/rag_service.py` -> `generate_summary()`](file:///d:/document-management-system/backend/rag_service.py):

#### System Prompt:
```text
You are an executive document analyst powered by Azure OpenAI ({deployment_label}).
Generate a structured, concise executive summary of the document excerpt provided below.
Format with:
- **Core Objective / Overview** (1-2 sentences)
- **Key Highlights & Takeaways** (3-5 bullet points)
- **Important Notes, Requirements, or Metrics**
```

#### User Prompt Template:
```text
Document excerpt:
{combined_document_chunks_up_to_8}

Please generate a clear executive summary:
```

#### Key Design Rationales:
- Standardizes diverse document types (financial CSVs, scientific PDFs, technical specifications) into an actionable executive briefing.
- Output uses clean markdown subheaders and bullet points rendered natively in the frontend modal.

---

### 2.3 Azure OpenAI Connectivity Ping Prompt

Located in [`backend/rag_service.py` -> `test_azure_openai_connection()`](file:///d:/document-management-system/backend/rag_service.py):

#### Test Prompt:
```json
{
  "messages": [
    {"role": "user", "content": "Respond with 'CONNECTION_SUCCESSFUL'."}
  ],
  "max_completion_tokens": 25
}
```

#### Key Design Rationales:
- Ultra-low latency ping (~100-300ms) to verify API key validity, deployment name existence, and endpoint reachability without incurring token costs.
- Captures exact Azure HTTP error codes (e.g., `401 Unauthorized`, `404 DeploymentNotFound`, `429 QuotaLimit`) and surfaces them to the UI.

---

### 2.4 Local Extraction & Fallback Heuristic

When Azure OpenAI is unreachable or unconfigured, the system runs an algorithmic sentence-scoring heuristic:

```python
score = 0.0
# Exact query match boost
if len(query_lower) > 5 and query_lower in sentence_lower:
    score += 5.0
# Token overlap with length weighting
for token in query_tokens:
    if token in sentence_lower:
        score += 1.0 + (len(token) * 0.15)
# Numeric boost for quantitative questions
if any(w in query_lower for w in ["when", "year", "date", "how many", "how much", "number"]):
    if re.search(r'\b\d+(?:[\.,]\d+)?\b', sentence):
        score += 2.5
# Entity boost for proper noun questions
if any(w in query_lower for w in ["who", "which company", "which processor", "what processor"]):
    if re.search(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', sentence):
        score += 2.0
```

---

## 3. Multi-Turn Conversational Memory Prompting

When a user asks follow-up questions (e.g., *"How many qubits did it use?"* following *"What did Google demonstrate in 2019?"*), previous turns are injected into the messages array:

```json
[
  {
    "role": "system",
    "content": "You are an intelligent Document Assistant powered by Azure OpenAI..."
  },
  {
    "role": "user",
    "content": "What did Google Quantum AI demonstrate in 2019?"
  },
  {
    "role": "assistant",
    "content": "Google Quantum AI demonstrated quantum supremacy using the 53-qubit Sycamore processor in 2019. [Document: quantum_computing_overview.pdf, Page 1]"
  },
  {
    "role": "user",
    "content": "Document Context:\n...\n\nQuestion: How many qubits did it use?\n\nAnswer:"
  }
]
```

---

## 4. 20 Evaluation Benchmark Prompts

The benchmark suite in [`backend/benchmark_eval.py`](file:///d:/document-management-system/backend/benchmark_eval.py) tests the RAG pipeline across three categories:

### Fact Retrieval Prompts

| # | Benchmark Prompt | Expected Ground Truth | Target Document | Expected Page |
|---|---|---|---|---|
| **Q1** | *"What did Google Quantum AI demonstrate in 2019?"* | 53-qubit Sycamore processor, quantum supremacy | `quantum_computing_overview.pdf` | Page 1 |
| **Q2** | *"What speedup does Grover's algorithm provide?"* | Quadratic speedup for unstructured database search | `quantum_computing_overview.pdf` | Page 2 |
| **Q3** | *"What algorithm can factor large integers exponentially faster?"* | Shor's algorithm | `quantum_computing_overview.pdf` | Page 2 |
| **Q4** | *"How many physical qubits are needed per logical qubit in fault-tolerant computing?"* | Thousands of physical qubits | `quantum_computing_overview.pdf` | Page 2 |
| **Q5** | *"What encryption standard is required by the AI policy?"* | AES-256 standard | `sample_ai_policy.txt` | Page 1 |
| **Q6** | *"How long can authentication tokens last before expiring?"* | 24 hours | `sample_ai_policy.txt` | Page 1 |
| **Q7** | *"Does the AI policy allow User A to see User B's documents?"* | No, strict user data isolation | `sample_ai_policy.txt` | Page 1 |
| **Q8** | *"What must accompany every factual statement in RAG answers according to the policy?"* | Originating document name and specific page number | `sample_ai_policy.txt` | Page 1 |
| **Q9** | *"What is the project budget specified in the requirements?"* | Open-Source | `project_requirements.docx` | Page 1 |
| **Q10** | *"What file formats must the document extraction support?"* | PDF, DOCX, TXT, Excel, CSV, JSON | `project_requirements.docx` | Page 1 |
| **Q11** | *"What vector store is specified in the requirements?"* | ChromaDB | `project_requirements.docx` | Page 1 |
| **Q12** | *"What is the deadline mentioned in the project specification?"* | November 2026 | `project_requirements.docx` | Page 1 |
| **Q13** | *"What is a qubit's superposition state?"* | Linear combination of 0 and 1 states | `quantum_computing_overview.pdf` | Page 1 |
| **Q14** | *"What type of codes are required for quantum error correction?"* | Surface codes | `quantum_computing_overview.pdf` | Page 2 |
| **Q15** | *"What should the system say if an answer is not in the documents?"* | Explicitly state that the answer is not found | `sample_ai_policy.txt` | Page 1 |
| **Q18** | *"What are the three main deliverables of the project?"* | 1. Fast text extraction 2. ChromaDB embeddings 3. Multi-turn QA with citations | `project_requirements.docx` | Page 1 |
| **Q19** | *"What was the revenue and net profit reported for Q2 2026?"* | Revenue: $1,480,000, Net Profit: $410,000 | `quarterly_financials.csv` | Page 1 |
| **Q20** | *"Which cloud resource runs Azure OpenAI Service in East US?"* | Resource ID: vm-ai-rag-01 ($850/mo, tier gpt-5.6-luna) | `cloud_infrastructure_inventory.xlsx` | Page 1 |

---

### Negative Constraint & Anti-Hallucination Prompts

These tests verify that when asked about out-of-domain knowledge, the model strictly refuses to hallucinate:

| # | Negative Test Prompt | Expected System Behavior |
|---|---|---|
| **Q16** | *"Who is the President of Mars?"* | Assistant explicitly responds that the information is not found in the uploaded documents. |
| **Q17** | *"What is the recipe for chocolate cake?"* | Assistant explicitly responds that the information is not found in the uploaded documents. |

---

## 5. Prompt Engineering Best Practices for Azure OpenAI

1. **Adaptive Token Parameters**:
   - Modern reasoning models (e.g., `gpt-5.6-luna`, `o1`, `o3`) require `max_completion_tokens`.
   - Older models (e.g., `gpt-4`, `gpt-35-turbo`) expect `max_tokens` and custom `temperature`.
   - The DMS RAG service automatically adapts to whichever model is deployed on the user's Azure resource.

2. **Context Window Optimization**:
   - Chunks are sized at ~700 characters with 150-character sliding overlap.
   - `top_k=6` provides ~4,200 characters of dense, high-signal context without overwhelming the attention window.

3. **Explicit Citation Formatting**:
   - Prefixing every chunk with `[Document: filename | Page X]` provides the model with exact citation anchors.
   - The React frontend matches this syntax via regular expressions to render interactive source pill badges.
