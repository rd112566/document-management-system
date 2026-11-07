import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from main import app

def run_tests():
    client = TestClient(app)

    # 1. Login
    login = client.post('/api/auth/login', json={'username': 'azure_test_user', 'password': 'Password123!'})
    token = login.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}'}
    print("[1] Logged in successfully. Token acquired.")

    # 2. Upload document
    pdf_path = os.path.join(os.path.dirname(__file__), "..", "samples", "quantum_computing_overview.pdf")
    with open(pdf_path, 'rb') as f:
        r = client.post(
            '/api/documents/upload',
            files={'file': ('quantum_computing_overview.pdf', f, 'application/pdf')},
            headers=headers
        )
    upload_data = r.json()
    doc_id = upload_data.get('id')
    print(f"[2] Uploaded document. doc_id: {doc_id}, chunks_indexed: {upload_data.get('chunks_indexed')}")

    # 3. Get Chunks
    chunks_res = client.get(f'/api/documents/{doc_id}/chunks', headers=headers)
    chunks_data = chunks_res.json()
    print(f"[3] Document chunks total: {chunks_data.get('total_chunks')}")
    if chunks_data.get('chunks'):
        print(f"    Sample chunk 1 (Page {chunks_data['chunks'][0]['page']}): {chunks_data['chunks'][0]['text'][:80]}...")

    # 4. Chat Query
    chat_res = client.post(
        '/api/chat',
        json={'question': 'What did Google demonstrate in 2019?', 'document_id': doc_id},
        headers=headers
    )
    chat_data = chat_res.json()
    print(f"[4] Chat response answer: {chat_data.get('answer')}")
    print(f"    Model used: {chat_data.get('model_used')}")
    print(f"    Citations count: {len(chat_data.get('citations', []))}")
    for idx, cite in enumerate(chat_data.get('citations', []), start=1):
        print(f"      Cite {idx}: {cite.get('document_name')} (Page {cite.get('page')}) -> {cite.get('snippet')[:60]}...")

    # 5. Document Summary
    summary_res = client.post(f'/api/documents/{doc_id}/summary', headers=headers)
    print(f"[5] Summary result: {summary_res.json().get('summary')[:120]}...")

    print("\nALL BACKEND E2E CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()

