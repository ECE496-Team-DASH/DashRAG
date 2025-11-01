# DashRAG API Examples & Usage Guide

Complete guide with real-world examples for every endpoint.

## Table of Contents
- [Getting Started](#getting-started)
- [Session Management](#session-management)
- [Document Ingestion](#document-ingestion)
- [Querying the Knowledge Graph](#querying-the-knowledge-graph)
- [Complete Workflows](#complete-workflows)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)

---

## Getting Started

### Base URL
```
Local dev: http://localhost:8000
Production: https://your-domain.com
```

### Interactive Documentation
```
Swagger UI: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc
OpenAPI Schema: http://localhost:8000/openapi.json
```

### Health Check
```bash
curl http://localhost:8000/healthz
```

**Response:**
```json
{
  "ok": true,
  "data_root": "/app/data",
  "can_write_data_root": true,
  "free_space_mb": 15360
}
```

---

## Session Management

### 1. Create a Session

**Purpose:** Start a new chat with an isolated knowledge graph.

```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"title": "LLM Architecture Research"}'
```

**Response:**
```json
{
  "id": "sess_a1b2c3d4e5f6",
  "title": "LLM Architecture Research",
  "settings": {},
  "stats": {
    "doc_count": 0
  }
}
```

**Python:**
```python
import requests

response = requests.post(
    "http://localhost:8000/sessions",
    json={"title": "LLM Architecture Research"}
)
session = response.json()
session_id = session["id"]
print(f"Created session: {session_id}")
```

**JavaScript:**
```javascript
const response = await fetch('http://localhost:8000/sessions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ title: 'LLM Architecture Research' })
});
const session = await response.json();
console.log('Session ID:', session.id);
```

---

### 2. List All Sessions

```bash
curl http://localhost:8000/sessions
```

**Response:**
```json
[
  {
    "id": "sess_a1b2c3d4e5f6",
    "title": "LLM Architecture Research",
    "settings": {}
  },
  {
    "id": "sess_f6e5d4c3b2a1",
    "title": "Climate Change Analysis",
    "settings": {}
  }
]
```

---

### 3. Get Session Details

```bash
curl "http://localhost:8000/sessions/detail?sid=sess_a1b2c3d4e5f6"
```

**Response:**
```json
{
  "id": "sess_a1b2c3d4e5f6",
  "title": "LLM Architecture Research",
  "settings": {},
  "stats": {
    "graph_exists": true
  }
}
```

---

### 4. Export Session

**Download as ZIP file:**
```bash
curl -o session_backup.zip \
  "http://localhost:8000/sessions/export?sid=sess_a1b2c3d4e5f6"
```

**Python:**
```python
import requests

response = requests.get(
    f"http://localhost:8000/sessions/export?sid={session_id}",
    stream=True
)

with open("session_backup.zip", "wb") as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)

print("Session exported successfully")
```

---

### 5. Delete Session

**Warning:** This is permanent and deletes all data!

```bash
curl -X DELETE "http://localhost:8000/sessions?sid=sess_a1b2c3d4e5f6"
```

**Response:**
```json
{
  "ok": true
}
```

---

## Document Ingestion

### 1. Upload PDF Files

**Single file upload:**
```bash
curl -X POST \
  "http://localhost:8000/documents/upload?sid=sess_a1b2c3d4e5f6" \
  -F "file=@transformer_paper.pdf"
```

**Response:**
```json
{
  "id": "doc_abc123def456",
  "status": "ready",
  "title": "transformer_paper.pdf"
}
```

**Python (single file):**
```python
import requests

session_id = "sess_a1b2c3d4e5f6"

with open("transformer_paper.pdf", "rb") as f:
    response = requests.post(
        f"http://localhost:8000/documents/upload?sid={session_id}",
        files={"file": f}
    )

doc = response.json()
print(f"Uploaded: {doc['title']} (Status: {doc['status']})")
```

**Python (multiple files):**
```python
import requests
from pathlib import Path

session_id = "sess_a1b2c3d4e5f6"
pdf_files = Path("./papers").glob("*.pdf")

for pdf_path in pdf_files:
    print(f"Uploading {pdf_path.name}...")
    
    with open(pdf_path, "rb") as f:
        response = requests.post(
            f"http://localhost:8000/documents/upload?sid={session_id}",
            files={"file": f}
        )
    
    doc = response.json()
    print(f"  → {doc['status']}: {doc['id']}")
```

---

### 2. Search arXiv Papers

**Search without adding (preview):**
```bash
curl "http://localhost:8000/documents/search-arxiv?sid=sess_a1b2c3d4e5f6&query=transformer+attention&max_results=3"
```

**Response:**
```json
[
  {
    "arxiv_id": "1706.03762",
    "title": "Attention Is All You Need",
    "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
    "abstract": "The dominant sequence transduction models...",
    "published_at": "2017-06-12",
    "pdf_url": "http://arxiv.org/pdf/1706.03762"
  }
]
```

**Global search (not session-specific):**
```bash
curl "http://localhost:8000/papers/search?query=large+language+models&max_results=5"
```

**Python:**
```python
import requests

# Search papers
response = requests.get(
    "http://localhost:8000/papers/search",
    params={
        "query": "transformer attention mechanism",
        "max_results": 5
    }
)

papers = response.json()
for paper in papers:
    print(f"[{paper['arxiv_id']}] {paper['title']}")
    print(f"  Authors: {', '.join(paper['authors'][:3])}")
    print()
```

---

### 3. Add arXiv Paper

**Add specific paper by ID:**
```bash
curl -X POST \
  "http://localhost:8000/documents/add-arxiv?sid=sess_a1b2c3d4e5f6" \
  -H "Content-Type: application/json" \
  -d '{"arxiv_id": "1706.03762"}'
```

**Response:**
```json
{
  "id": "doc_xyz789uvw012",
  "status": "ready",
  "arxiv_id": "1706.03762"
}
```

**Python (search and add):**
```python
import requests

session_id = "sess_a1b2c3d4e5f6"

# 1. Search for papers
papers = requests.get(
    "http://localhost:8000/papers/search",
    params={"query": "BERT language model", "max_results": 3}
).json()

# 2. Let user select papers (or auto-select)
for paper in papers:
    print(f"Adding: {paper['title']}")
    
    response = requests.post(
        f"http://localhost:8000/documents/add-arxiv?sid={session_id}",
        json={"arxiv_id": paper["arxiv_id"]}
    )
    
    doc = response.json()
    print(f"  → Status: {doc['status']}")
```

---

### 4. List Documents

**Get all documents in session:**
```bash
curl "http://localhost:8000/documents?sid=sess_a1b2c3d4e5f6"
```

**Response:**
```json
[
  {
    "id": "doc_abc123def456",
    "title": "transformer_paper.pdf",
    "source_type": "upload",
    "status": "ready",
    "arxiv_id": null,
    "pages": 15
  },
  {
    "id": "doc_xyz789uvw012",
    "title": "Attention Is All You Need",
    "source_type": "arxiv",
    "status": "ready",
    "arxiv_id": "1706.03762",
    "pages": 12
  }
]
```

**Check document status:**
```python
import requests
import time

session_id = "sess_a1b2c3d4e5f6"

# Poll until all documents are ready
while True:
    docs = requests.get(
        f"http://localhost:8000/documents",
        params={"sid": session_id}
    ).json()
    
    statuses = [doc["status"] for doc in docs]
    print(f"Document statuses: {statuses}")
    
    if all(s == "ready" for s in statuses):
        print("All documents ready!")
        break
    
    if any(s == "error" for s in statuses):
        print("Error processing some documents")
        break
    
    time.sleep(5)  # Wait 5 seconds before checking again
```

---

## Querying the Knowledge Graph

### 1. Non-Streaming Query

**Local mode (specific chunks):**
```bash
curl -X POST \
  "http://localhost:8000/messages?sid=sess_a1b2c3d4e5f6" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "What is the self-attention mechanism?",
    "mode": "local",
    "top_k": 10
  }'
```

**Global mode (cross-document synthesis):**
```bash
curl -X POST \
  "http://localhost:8000/messages?sid=sess_a1b2c3d4e5f6" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Summarize the main themes across all papers",
    "mode": "global",
    "top_k": 15
  }'
```

**Response:**
```json
{
  "message": {
    "id": "msg_asst_xyz789",
    "role": "assistant",
    "content": {
      "text": "Based on the knowledge graph, the self-attention mechanism..."
    }
  }
}
```

**Python:**
```python
import requests

session_id = "sess_a1b2c3d4e5f6"

# Query the knowledge graph
response = requests.post(
    f"http://localhost:8000/messages",
    params={"sid": session_id},
    json={
        "content": "What are the key innovations in transformer architecture?",
        "mode": "global",
        "top_k": 15
    }
)

message = response.json()["message"]
print(f"AI Response:\n{message['content']['text']}")
```

---

### 2. Streaming Query (SSE)

**Python:**
```python
import requests
import json

session_id = "sess_a1b2c3d4e5f6"

response = requests.post(
    f"http://localhost:8000/messages/stream",
    params={"sid": session_id},
    json={
        "content": "Compare attention mechanisms across papers",
        "mode": "global"
    },
    stream=True
)

print("AI Response: ", end="", flush=True)

for line in response.iter_lines():
    if line.startswith(b"data: "):
        data = json.loads(line[6:])
        
        if data["type"] == "token":
            print(data["text"], end="", flush=True)
        elif data["type"] == "done":
            print("\n[Complete]")
            break
        elif data["type"] == "error":
            print(f"\nError: {data['message']}")
            break
```

**JavaScript (browser):**
```javascript
const eventSource = new EventSource(
  'http://localhost:8000/messages/stream?sid=sess_a1b2c3d4e5f6'
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'token') {
    document.getElementById('response').innerText += data.text;
  } else if (data.type === 'done') {
    eventSource.close();
    console.log('Stream complete');
  } else if (data.type === 'error') {
    console.error('Error:', data.message);
    eventSource.close();
  }
};

eventSource.onerror = (error) => {
  console.error('SSE error:', error);
  eventSource.close();
};
```

**JavaScript (Node.js with fetch):**
```javascript
const response = await fetch(
  'http://localhost:8000/messages/stream?sid=sess_abc',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      content: 'Summarize findings',
      mode: 'global'
    })
  }
);

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      
      if (data.type === 'token') {
        process.stdout.write(data.text);
      } else if (data.type === 'done') {
        console.log('\n[Complete]');
      }
    }
  }
}
```

---

### 3. Get Chat History

```bash
curl "http://localhost:8000/messages?sid=sess_a1b2c3d4e5f6"
```

**Response:**
```json
[
  {
    "id": "msg_user_abc123",
    "role": "user",
    "content": {
      "text": "What are the key innovations?"
    }
  },
  {
    "id": "msg_asst_def456",
    "role": "assistant",
    "content": {
      "text": "The key innovations include..."
    }
  }
]
```

---

## Complete Workflows

### Workflow 1: Research Assistant (PDF Upload)

```python
import requests
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"

# 1. Create session
print("Creating session...")
session = requests.post(f"{BASE_URL}/sessions", json={
    "title": "Research Papers Analysis"
}).json()
sid = session["id"]
print(f"✓ Session created: {sid}")

# 2. Upload PDFs
pdf_dir = Path("./research_papers")
pdf_files = list(pdf_dir.glob("*.pdf"))

print(f"\nUploading {len(pdf_files)} PDFs...")
for pdf_path in pdf_files:
    with open(pdf_path, "rb") as f:
        doc = requests.post(
            f"{BASE_URL}/documents/upload?sid={sid}",
            files={"file": f}
        ).json()
    print(f"  ✓ {pdf_path.name} → {doc['status']}")

# 3. Wait for processing
print("\nProcessing documents...")
while True:
    docs = requests.get(f"{BASE_URL}/documents", params={"sid": sid}).json()
    statuses = [d["status"] for d in docs]
    
    if all(s == "ready" for s in statuses):
        print("✓ All documents ready!")
        break
    
    print(f"  Status: {statuses}")
    time.sleep(5)

# 4. Query the knowledge graph
print("\nQuerying knowledge graph...")
queries = [
    "What are the main methodologies used in these papers?",
    "Summarize the key findings across all papers",
    "What are the limitations mentioned?"
]

for query in queries:
    print(f"\nQ: {query}")
    
    response = requests.post(
        f"{BASE_URL}/messages",
        params={"sid": sid},
        json={"content": query, "mode": "global", "top_k": 15}
    ).json()
    
    answer = response["message"]["content"]["text"]
    print(f"A: {answer[:200]}...")  # Print first 200 chars

# 5. Export session
print("\nExporting session...")
export_response = requests.get(f"{BASE_URL}/sessions/export", params={"sid": sid})
with open(f"session_export_{sid}.zip", "wb") as f:
    f.write(export_response.content)
print("✓ Session exported!")
```

---

### Workflow 2: arXiv Literature Review

```python
import requests
import time

BASE_URL = "http://localhost:8000"

# 1. Create session
session = requests.post(f"{BASE_URL}/sessions", json={
    "title": "Transformer Architecture Survey"
}).json()
sid = session["id"]
print(f"Session: {sid}")

# 2. Search arXiv
print("\nSearching arXiv...")
papers = requests.get(f"{BASE_URL}/papers/search", params={
    "query": "transformer attention mechanism survey",
    "max_results": 5
}).json()

print(f"Found {len(papers)} papers:")
for i, paper in enumerate(papers, 1):
    print(f"{i}. [{paper['arxiv_id']}] {paper['title']}")

# 3. Add papers to session
print("\nAdding papers to knowledge graph...")
for paper in papers:
    print(f"  Adding {paper['arxiv_id']}...", end=" ")
    
    doc = requests.post(
        f"{BASE_URL}/documents/add-arxiv?sid={sid}",
        json={"arxiv_id": paper["arxiv_id"]}
    ).json()
    
    print(doc["status"])

# 4. Wait for processing
print("\nWaiting for processing...")
while True:
    docs = requests.get(f"{BASE_URL}/documents", params={"sid": sid}).json()
    ready = sum(1 for d in docs if d["status"] == "ready")
    total = len(docs)
    
    print(f"  {ready}/{total} ready", end="\r")
    
    if ready == total:
        print(f"\n✓ All {total} papers ready!")
        break
    
    time.sleep(5)

# 5. Run comparative analysis
print("\nRunning analysis...")
analyses = [
    ("Overview", "Provide a high-level overview of the transformer architecture based on these papers"),
    ("Innovations", "What are the key innovations and improvements mentioned across papers?"),
    ("Applications", "What applications of transformers are discussed?"),
    ("Challenges", "What challenges and limitations are identified?")
]

for title, query in analyses:
    print(f"\n{'='*60}")
    print(f"{title}")
    print('='*60)
    
    response = requests.post(
        f"{BASE_URL}/messages",
        params={"sid": sid},
        json={"content": query, "mode": "global", "top_k": 20}
    ).json()
    
    print(response["message"]["content"]["text"])

# 6. Get conversation history
print("\n\nConversation History:")
messages = requests.get(f"{BASE_URL}/messages", params={"sid": sid}).json()
print(f"Total messages: {len(messages)}")
```

---

### Workflow 3: Interactive Chat with Streaming

```python
import requests
import json

BASE_URL = "http://localhost:8000"

def stream_query(session_id, question, mode="local"):
    """Query with streaming response"""
    response = requests.post(
        f"{BASE_URL}/messages/stream",
        params={"sid": session_id},
        json={"content": question, "mode": mode},
        stream=True
    )
    
    print(f"\nAI: ", end="", flush=True)
    
    for line in response.iter_lines():
        if line.startswith(b"data: "):
            data = json.loads(line[6:])
            
            if data["type"] == "token":
                print(data["text"], end="", flush=True)
            elif data["type"] == "done":
                print("\n")
                break

# Setup session (assume already created with documents)
session_id = "sess_a1b2c3d4e5f6"

# Interactive chat
print("="*60)
print("DashRAG Interactive Chat")
print("="*60)
print("Commands: 'quit' to exit, 'mode:local' or 'mode:global' to change")
print()

current_mode = "local"

while True:
    user_input = input("You: ").strip()
    
    if user_input.lower() == "quit":
        break
    
    if user_input.startswith("mode:"):
        current_mode = user_input.split(":")[1]
        print(f"Switched to {current_mode} mode")
        continue
    
    if not user_input:
        continue
    
    stream_query(session_id, user_input, mode=current_mode)
```

---

## Error Handling

### Common Errors and Solutions

**1. Session Not Found (404)**
```python
try:
    response = requests.get(f"{BASE_URL}/sessions/{session_id}")
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 404:
        print("Session not found. Please create a new session.")
    else:
        print(f"Error: {e}")
```

**2. No Ready Documents (400)**
```python
try:
    response = requests.post(
        f"{BASE_URL}/sessions/{sid}/messages",
        json={"content": "What are the findings?"}
    )
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 400:
        error = e.response.json()
        if "ready document" in error.get("detail", "").lower():
            print("Please add and process documents before querying")
```

**3. Invalid File Format (400)**
```python
import requests

def upload_pdf_safe(session_id, file_path):
    """Upload PDF with error handling"""
    if not file_path.lower().endswith('.pdf'):
        print("Error: Only PDF files are supported")
        return None
    
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/sessions/{session_id}/documents/upload",
                files={"file": f}
            )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"Upload failed: {e.response.json()}")
        return None
```

**4. Network/Timeout Errors**
```python
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def create_session_with_retry():
    """Create session with automatic retries"""
    session = requests.Session()
    
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    )
    
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    return session

# Usage
http_session = create_session_with_retry()
response = http_session.post(
    f"{BASE_URL}/sessions",
    json={"title": "My Session"},
    timeout=30
)
```

---

## Best Practices

### 1. Session Management
```python
# Always store session IDs
import json

session_map = {}

def create_and_track_session(title):
    response = requests.post(f"{BASE_URL}/sessions", json={"title": title})
    session = response.json()
    
    # Store session ID
    session_map[title] = session["id"]
    
    # Persist to file
    with open("sessions.json", "w") as f:
        json.dump(session_map, f)
    
    return session["id"]

# Load saved sessions
try:
    with open("sessions.json", "r") as f:
        session_map = json.load(f)
except FileNotFoundError:
    session_map = {}
```

### 2. Document Processing
```python
def wait_for_documents_ready(session_id, timeout=300, poll_interval=5):
    """Wait for all documents to be processed"""
    import time
    
    start = time.time()
    
    while time.time() - start < timeout:
        docs = requests.get(
            f"{BASE_URL}/sessions/{session_id}/documents"
        ).json()
        
        if not docs:
            time.sleep(poll_interval)
            continue
        
        statuses = [d["status"] for d in docs]
        
        if all(s == "ready" for s in statuses):
            return True, docs
        
        if any(s == "error" for s in statuses):
            errors = [d for d in docs if d["status"] == "error"]
            return False, errors
        
        time.sleep(poll_interval)
    
    return False, "Timeout waiting for documents"

# Usage
success, result = wait_for_documents_ready(session_id)
if success:
    print(f"All {len(result)} documents ready")
else:
    print(f"Error: {result}")
```

### 3. Query Optimization
```python
# Choose the right mode for your use case
def smart_query(session_id, question):
    """Choose query mode based on question type"""
    
    # Questions that benefit from global mode
    global_keywords = [
        "summarize", "overall", "across", "compare",
        "themes", "trends", "synthesis", "all papers"
    ]
    
    # Check if question needs global analysis
    use_global = any(kw in question.lower() for kw in global_keywords)
    
    mode = "global" if use_global else "local"
    top_k = 20 if use_global else 10
    
    print(f"Using {mode} mode")
    
    return requests.post(
        f"{BASE_URL}/sessions/{session_id}/messages",
        json={
            "content": question,
            "mode": mode,
            "top_k": top_k
        }
    ).json()
```

### 4. Batch Operations
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def upload_pdfs_parallel(session_id, pdf_paths, max_workers=3):
    """Upload multiple PDFs in parallel"""
    
    def upload_one(pdf_path):
        with open(pdf_path, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/sessions/{session_id}/documents/upload",
                files={"file": f}
            )
        return pdf_path.name, response.json()
    
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(upload_one, path): path 
            for path in pdf_paths
        }
        
        for future in as_completed(futures):
            filename, result = future.result()
            print(f"✓ {filename}: {result['status']}")
            results.append(result)
    
    return results
```

### 5. Resource Cleanup
```python
import atexit

# Track sessions for cleanup
active_sessions = set()

def create_session_tracked(title):
    session = requests.post(
        f"{BASE_URL}/sessions",
        json={"title": title}
    ).json()
    active_sessions.add(session["id"])
    return session

def cleanup_sessions():
    """Cleanup on exit"""
    for sid in active_sessions:
        try:
            requests.delete(f"{BASE_URL}/sessions/{sid}")
            print(f"Cleaned up session {sid}")
        except Exception as e:
            print(f"Failed to cleanup {sid}: {e}")

# Register cleanup
atexit.register(cleanup_sessions)
```

---

## Query Mode Guidelines

### Local Mode
**Best for:**
- Specific factual questions
- Finding exact quotes or citations
- Targeted information retrieval
- Fast responses

**Example questions:**
- "What dataset was used in paper X?"
- "How is the attention mechanism implemented?"
- "What are the hyperparameters mentioned?"

### Global Mode
**Best for:**
- Cross-document synthesis
- Identifying common themes
- Comparative analysis
- High-level summaries

**Example questions:**
- "What are the common approaches across all papers?"
- "Summarize the evolution of transformer architectures"
- "Compare the evaluation metrics used"

### Naive Mode
**Best for:**
- Quick keyword searches
- When you need very fast responses
- Simple lookups

**Example questions:**
- "Find mentions of BERT"
- "List papers about GPT"

---

## Rate Limiting & Performance

### Tips for Production Use

1. **Implement client-side throttling:**
```python
import time
from functools import wraps

def rate_limit(calls_per_second=2):
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            wait = min_interval - elapsed
            if wait > 0:
                time.sleep(wait)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator

@rate_limit(calls_per_second=2)
def query_api(session_id, question):
    return requests.post(
        f"{BASE_URL}/sessions/{session_id}/messages",
        json={"content": question}
    ).json()
```

2. **Cache responses:**
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_query(session_id, question, mode="local"):
    response = requests.post(
        f"{BASE_URL}/sessions/{session_id}/messages",
        json={"content": question, "mode": mode}
    )
    return response.json()
```

3. **Monitor document processing:**
```python
def monitor_processing(session_id):
    """Real-time monitoring of document processing"""
    import sys
    
    while True:
        docs = requests.get(
            f"{BASE_URL}/sessions/{session_id}/documents"
        ).json()
        
        total = len(docs)
        ready = sum(1 for d in docs if d["status"] == "ready")
        processing = sum(1 for d in docs if d["status"] in ["inserting", "downloading"])
        errors = sum(1 for d in docs if d["status"] == "error")
        
        status = f"Ready: {ready}/{total} | Processing: {processing} | Errors: {errors}"
        sys.stdout.write(f"\r{status}")
        sys.stdout.flush()
        
        if ready == total or (ready + errors == total):
            print()  # New line
            break
        
        time.sleep(2)
```

---

For more information, see the main [README.md](./README.md) or visit `/docs` for interactive documentation.
