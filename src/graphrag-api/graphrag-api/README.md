
# DashRAG Chat API (FastAPI + nano-graphrag)

A session-based chatbot that builds a per-session knowledge graph using **nano-graphrag**.

- One knowledge graph per chat **session** (filesystem-backed).
- **Doc ingestion**: upload PDFs or fetch from arXiv, extract text, then `GraphRAG.insert(str|list[str])`.
- **Query**: `GraphRAG.query(prompt, QueryParam(...))` in `local|global|naive` modes.
- DB: SQLite by default; switch to Postgres via `DATABASE_URL`.
- CORS enabled for local dev.

---

## Table of Contents
- [Quick Start](#quick-start)
- [API Documentation](#api-documentation)
  - [Sessions](#sessions)
  - [Documents](#documents)
  - [Messages (Query)](#messages-query)
  - [Papers (arXiv Search)](#papers-arxiv-search)
- [Typical Workflows](#typical-workflows)
- [Configuration](#configuration)

> 📚 **Additional Documentation:**
> - [API Examples & Code Samples](./API_EXAMPLES.md) - Complete working examples in Python, JavaScript, cURL
> - [API Reference](./API_REFERENCE.md) - Detailed schemas, parameters, and error codes
> - [Interactive Docs](http://localhost:8000/docs) - Swagger UI (when server is running)

---

## Quick Start

### Local Development

```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and set at least one model provider:
#   - GEMINI_API_KEY (for Google Gemini)
#   - OPENAI_API_KEY (for OpenAI)
#   - AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT (for Azure OpenAI)

# 4. Run the server
uvicorn app.main:app --reload

# 5. Open interactive API docs
# http://localhost:8000/docs
```

### Docker

```bash
cp .env.example .env
# Edit .env with your API keys
docker compose up --build
# API available at http://localhost:8000
```

---

## API Documentation

### Sessions

Sessions are isolated chat contexts, each with its own knowledge graph.

#### **POST /sessions**
Create a new session.

**Request Body:**
```json
{
  "title": "Healthcare LLMs Research"
}
```

**Response (201):**
```json
{
  "id": "sess_a1b2c3d4e5f6",
  "title": "Healthcare LLMs Research",
  "settings": {},
  "stats": {
    "doc_count": 0
  }
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"title": "My Research Session"}'
```

---

#### **GET /sessions**
List all sessions.

**Response (200):**
```json
[
  {
    "id": "sess_a1b2c3d4e5f6",
    "title": "Healthcare LLMs Research",
    "settings": {}
  },
  {
    "id": "sess_f6e5d4c3b2a1",
    "title": "Climate Change Papers",
    "settings": {}
  }
]
```

**Example (curl):**
```bash
curl http://localhost:8000/sessions
```

---

#### **GET /sessions/detail?sid={sid}**
Get details for a specific session.

**Response (200):**
```json
{
  "id": "sess_a1b2c3d4e5f6",
  "title": "Healthcare LLMs Research",
  "settings": {},
  "stats": {
    "graph_exists": true
  }
}
```

**Example (curl):**
```bash
curl "http://localhost:8000/sessions/detail?sid=sess_a1b2c3d4e5f6"
```

---

#### **DELETE /sessions?sid={sid}**
Delete a session and all its data (documents, messages, graph).

**Response (200):**
```json
{
  "ok": true
}
```

**Example (curl):**
```bash
curl -X DELETE "http://localhost:8000/sessions?sid=sess_a1b2c3d4e5f6"
```

---

#### **GET /sessions/export?sid={sid}**
Download session data as a ZIP file (includes graph and uploaded PDFs).

**Response:** ZIP file download

**Example (curl):**
```bash
curl -o session_export.zip \
  "http://localhost:8000/sessions/export?sid=sess_a1b2c3d4e5f6"
```

---

### Documents

Documents are PDFs added to a session's knowledge graph.

#### **GET /documents?sid={sid}**
List all documents in a session.

**Response (200):**
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

**Status values:**
- `pending` - Document created but not processed
- `downloading` - Downloading from arXiv
- `inserting` - Extracting text and building graph
- `ready` - Ready for querying
- `error` - Processing failed

**Example (curl):**
```bash
curl "http://localhost:8000/documents?sid=sess_a1b2c3d4e5f6"
```

---

#### **POST /documents/upload?sid={sid}**
Upload a PDF document to the session.

**Request:** Multipart form with `file` field (PDF)

**Response (200):**
```json
{
  "id": "doc_abc123def456",
  "status": "ready",
  "title": "my_paper.pdf"
}
```

**Example (curl):**
```bash
curl -X POST \
  "http://localhost:8000/documents/upload?sid=sess_a1b2c3d4e5f6" \
  -F "file=@/path/to/paper.pdf"
```

**Example (Python):**
```python
import requests

session_id = "sess_a1b2c3d4e5f6"
with open("paper.pdf", "rb") as f:
    response = requests.post(
        f"http://localhost:8000/documents/upload?sid={session_id}",
        files={"file": f}
    )
print(response.json())
```

---

#### **GET /documents/search-arxiv?sid={sid}**
Search arXiv without adding documents (preview results).

**Query Parameters:**
- `sid` (required): Session ID
- `query` (required): Search query
- `max_results` (optional, default=5): Max papers to return

**Response (200):**
```json
[
  {
    "arxiv_id": "1706.03762",
    "title": "Attention Is All You Need",
    "authors": ["Ashish Vaswani", "Noam Shazeer", "..."],
    "abstract": "The dominant sequence transduction models...",
    "published_at": "2017-06-12",
    "pdf_url": "http://arxiv.org/pdf/1706.03762"
  }
]
```

**Example (curl):**
```bash
curl "http://localhost:8000/documents/search-arxiv?sid=sess_a1b2c3d4e5f6&query=transformer+attention&max_results=3"
```

---

#### **POST /documents/add-arxiv?sid={sid}**
Download and add an arXiv paper to the session.

**Request Body:**
```json
{
  "arxiv_id": "1706.03762"
}
```

**Response (200):**
```json
{
  "id": "doc_xyz789uvw012",
  "status": "ready",
  "arxiv_id": "1706.03762"
}
```

**Example (curl):**
```bash
curl -X POST \
  "http://localhost:8000/documents/add-arxiv?sid=sess_a1b2c3d4e5f6" \
  -H "Content-Type: application/json" \
  -d '{"arxiv_id": "1706.03762"}'
```

---

### Messages (Query)

Query the knowledge graph and get AI-generated responses.

#### **GET /messages?sid={sid}**
Get chat history for a session.

**Response (200):**
```json
[
  {
    "id": "msg_user_abc123",
    "role": "user",
    "content": {
      "text": "What are the main contributions of the transformer architecture?"
    }
  },
  {
    "id": "msg_asst_def456",
    "role": "assistant",
    "content": {
      "text": "The transformer architecture introduced several key innovations..."
    }
  }
]
```

**Example (curl):**
```bash
curl "http://localhost:8000/messages?sid=sess_a1b2c3d4e5f6"
```

---

#### **POST /messages?sid={sid}**
Query the knowledge graph (non-streaming).

**Request Body:**
```json
{
  "content": "Summarize the key findings across all papers",
  "mode": "global",
  "top_k": 10
}
```

**Query Parameters (all optional):**
- `mode`: `"local"` | `"global"` | `"naive"` (default: `"local"`)
  - **local**: Search specific text chunks
  - **global**: Community-based synthesis across documents
  - **naive**: Simple text matching
- `top_k`: Number of results to consider (default: 60)
- `level`: Community hierarchy level for global mode
- `response_type`: Type of response formatting
- `only_need_context`: Return context without LLM generation
- `include_text_chunks_in_context`: Include source chunks
- `global_max_consider_community`: Max communities in global mode
- `global_min_community_rating`: Min community rating threshold
- `naive_max_token_for_text_unit`: Max tokens for naive mode

**Response (200):**
```json
{
  "message": {
    "id": "msg_asst_xyz789",
    "role": "assistant",
    "content": {
      "text": "Based on the papers in this knowledge graph, the key findings are..."
    }
  }
}
```

**Example (curl):**
```bash
curl -X POST \
  http://localhost:8000/sessions/sess_a1b2c3d4e5f6/messages \
  -H "Content-Type: application/json" \
  -d '{
    "content": "What are the limitations of current LLM architectures?",
    "mode": "global",
    "top_k": 15
  }'
```

**Example (Python):**
```python
import requests

response = requests.post(
    "http://localhost:8000/messages?sid=sess_a1b2c3d4e5f6",
    json={
        "content": "Compare the attention mechanisms across papers",
        "mode": "local",
        "top_k": 10
    }
)
print(response.json()["message"]["content"]["text"])
```

---

#### **POST /messages/stream?sid={sid}**
Query with Server-Sent Events (SSE) streaming.

**Request Body:** Same as non-streaming endpoint

**Response:** SSE stream with events:
```
data: {"type": "token", "text": "Based on the papers..."}

data: {"type": "done"}
```

**Example (Python with streaming):**
```python
import requests
import json

response = requests.post(
    "http://localhost:8000/messages/stream?sid=sess_a1b2c3d4e5f6",
    json={"content": "Summarize the main findings", "mode": "global"},
    stream=True
)

for line in response.iter_lines():
    if line.startswith(b"data: "):
        data = json.loads(line[6:])
        if data["type"] == "token":
            print(data["text"], end="", flush=True)
        elif data["type"] == "done":
            print("\n[Stream complete]")
```

**Example (JavaScript/fetch):**
```javascript
const eventSource = new EventSource(
  'http://localhost:8000/messages/stream?sid=sess_a1b2c3d4e5f6'
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'token') {
    console.log(data.text);
  } else if (data.type === 'done') {
    eventSource.close();
  }
};
```

---

### Papers (arXiv Search)

Global arXiv search (not tied to a session).

#### **GET /papers/search**
Search arXiv papers.

**Query Parameters:**
- `query` (required): Search terms
- `max_results` (optional, default=10): Max results

**Response (200):**
```json
[
  {
    "arxiv_id": "1706.03762",
    "title": "Attention Is All You Need",
    "authors": ["Ashish Vaswani", "..."],
    "abstract": "The dominant sequence...",
    "published_at": "2017-06-12",
    "pdf_url": "http://arxiv.org/pdf/1706.03762"
  }
]
```

**Example (curl):**
```bash
curl "http://localhost:8000/papers/search?query=large+language+models&max_results=5"
```

---

## Typical Workflows

### Workflow 1: Create Session & Upload PDFs

```bash
# 1. Create a session
SESSION_ID=$(curl -s -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"title": "My Research"}' | jq -r '.id')

echo "Session ID: $SESSION_ID"

# 2. Upload PDFs
curl -X POST \
  "http://localhost:8000/documents/upload?sid=$SESSION_ID" \
  -F "file=@paper1.pdf"

curl -X POST \
  "http://localhost:8000/documents/upload?sid=$SESSION_ID" \
  -F "file=@paper2.pdf"

# 3. Check document status
curl "http://localhost:8000/documents?sid=$SESSION_ID"

# 4. Query the knowledge graph
curl -X POST \
  "http://localhost:8000/messages?sid=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "What are the main themes across these papers?",
    "mode": "global"
  }'
```

---

### Workflow 2: Research Assistant with arXiv

```python
import requests
import time

BASE_URL = "http://localhost:8000"

# 1. Create session
session = requests.post(f"{BASE_URL}/sessions", json={
    "title": "Transformer Architecture Research"
}).json()
sid = session["id"]
print(f"Created session: {sid}")

# 2. Search arXiv
papers = requests.get(f"{BASE_URL}/papers/search", params={
    "query": "transformer attention mechanism",
    "max_results": 3
}).json()

# 3. Add selected papers
for paper in papers:
    print(f"Adding: {paper['title']}")
    requests.post(
        f"{BASE_URL}/documents/add-arxiv?sid={sid}",
        json={"arxiv_id": paper["arxiv_id"]}
    )

# 4. Wait for processing (poll status)
while True:
    docs = requests.get(f"{BASE_URL}/documents", params={"sid": sid}).json()
    if all(d["status"] == "ready" for d in docs):
        print("All documents ready!")
        break
    print("Processing documents...")
    time.sleep(5)

# 5. Query with global mode (cross-document synthesis)
response = requests.post(f"{BASE_URL}/messages", params={"sid": sid}, json={
    "content": "Compare the attention mechanisms proposed in these papers",
    "mode": "global",
    "top_k": 15
}).json()

print("\nAnswer:")
print(response["message"]["content"]["text"])

# 6. Follow-up with local mode (specific details)
response = requests.post(f"{BASE_URL}/messages", params={"sid": sid}, json={
    "content": "What are the computational complexity advantages?",
    "mode": "local",
    "top_k": 10
}).json()

print("\nFollow-up:")
print(response["message"]["content"]["text"])
```

---

### Workflow 3: Export Session Data

```bash
SESSION_ID="sess_a1b2c3d4e5f6"

# Export session as ZIP
curl -o my_research_backup.zip \
  "http://localhost:8000/sessions/export?sid=$SESSION_ID"

# The ZIP contains:
# - graph/ (knowledge graph data)
# - uploads/ (original PDFs)
```

---

## Configuration

### Environment Variables

Create a `.env` file with:

```bash
# Database (optional, defaults to SQLite)
DATABASE_URL=sqlite:///./data/app.db
# Or for PostgreSQL:
# DATABASE_URL=postgresql://user:pass@localhost/dbname

# Data storage
DATA_ROOT=./data

# arXiv settings
ARXIV_MAX_RESULTS=20

# LLM Provider (choose one)

# Option 1: Google Gemini
GEMINI_API_KEY=your_gemini_key_here
# Or:
# GOOGLE_API_KEY=your_google_key_here

# Option 2: OpenAI
OPENAI_API_KEY=your_openai_key_here

# Option 3: Azure OpenAI
AZURE_OPENAI_API_KEY=your_azure_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Optional overrides
# NGR_USE_GEMINI=true
# NGR_USE_AZURE_OPENAI=true
```

### Query Modes Explained

- **`local`** (default): Best for specific questions about particular passages
  - Retrieves and reasons over specific text chunks
  - Fast, precise for targeted queries
  
- **`global`**: Best for broad synthesis and cross-document patterns
  - Uses community detection to find themes
  - Slower but better for "summarize all papers" type queries
  
- **`naive`**: Simple keyword matching
  - Fastest but least sophisticated
  - Good for quick lookups

### Provider Selection

The API auto-detects your LLM provider based on environment variables:

1. If `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` → Azure OpenAI
2. Else if `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) → Google Gemini
3. Else if `OPENAI_API_KEY` → OpenAI

Override with `NGR_USE_GEMINI=true` or `NGR_USE_AZURE_OPENAI=true` if needed.

---

## Interactive API Documentation

Visit **http://localhost:8000/docs** when the server is running for:

### Swagger UI (`/docs`)
- 🧪 Test all endpoints directly in browser
- 📋 See detailed request/response schemas
- 💻 Generate code snippets in multiple languages
- 📝 View parameter descriptions and examples

### ReDoc (`/redoc`)
- 📖 Alternative documentation interface
- 🎨 Clean, readable format
- 🔍 Better for browsing and reading

### OpenAPI Schema (`/openapi.json`)
- 📄 Download full OpenAPI 3.0 specification
- 🛠️ Import into Postman, Insomnia, etc.
- ⚙️ Generate client SDKs with OpenAPI Generator

---

## Documentation Overview

| Document | Purpose | Best For |
|----------|---------|----------|
| [README.md](./README.md) | Quick start & overview | Getting started, understanding concepts |
| [API_EXAMPLES.md](./API_EXAMPLES.md) | Code examples | Learning by example, copy-paste snippets |
| [API_REFERENCE.md](./API_REFERENCE.md) | Complete API reference | Parameter details, error codes, schemas |
| `/docs` (Swagger UI) | Interactive testing | Exploring API, running test requests |

---

## Endpoint Summary

Quick reference of all endpoints:

### Sessions
- `POST /sessions` - Create session
- `GET /sessions` - List all sessions
- `GET /sessions/{sid}` - Get session details
- `DELETE /sessions/{sid}` - Delete session
- `GET /sessions/{sid}/export` - Export as ZIP

### Documents
- `GET /sessions/{sid}/documents` - List documents
- `POST /sessions/{sid}/documents/upload` - Upload PDF
- `GET /sessions/{sid}/documents/search-arxiv` - Search arXiv
- `POST /sessions/{sid}/documents/add-arxiv` - Add arXiv paper

### Messages
- `GET /sessions/{sid}/messages` - Get chat history
- `POST /sessions/{sid}/messages` - Query (non-streaming)
- `POST /sessions/{sid}/messages/stream` - Query (SSE streaming)

### Papers
- `GET /papers/search` - Global arXiv search

### Health
- `GET /healthz` - Health check

---

## Troubleshooting

### Common Issues

**1. "Session not found" errors**
```python
# Always verify session exists before operations
response = requests.get(f"{BASE_URL}/sessions/{session_id}")
if response.status_code == 404:
    print("Session does not exist. Creating new one...")
    session = requests.post(f"{BASE_URL}/sessions", json={"title": "New Session"}).json()
```

**2. "No ready documents" when querying**
```python
# Check document status before querying
docs = requests.get(f"{BASE_URL}/sessions/{session_id}/documents").json()
ready_docs = [d for d in docs if d["status"] == "ready"]
if not ready_docs:
    print("Please add and process documents first")
```

**3. PDF upload fails**
- Ensure file is a valid PDF
- Check file size (< 20MB recommended)
- Verify session exists

**4. arXiv download fails**
- Verify arXiv ID format (e.g., "1706.03762")
- Check network connectivity
- arXiv may be temporarily unavailable

**5. Query takes too long**
- Use `local` mode instead of `global` for faster responses
- Reduce `top_k` parameter
- Consider adding documents in smaller batches

---

## Performance Tips

### For Faster Queries
1. **Use local mode** for specific questions
2. **Reduce top_k** to 5-10 for quick answers
3. **Add fewer documents** per session (10-20 papers optimal)

### For Better Answers
1. **Use global mode** for synthesis and themes
2. **Increase top_k** to 15-30 for comprehensive answers
3. **Use clear, specific questions**

### For Production
1. **Add rate limiting** middleware
2. **Enable caching** for repeated queries
3. **Use async workers** for document processing
4. **Monitor disk space** (knowledge graphs grow over time)

---

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
```bash
black app/
ruff check app/
```

### Environment
```bash
# Development
DEBUG=true
LOG_LEVEL=debug

# Production
DEBUG=false
LOG_LEVEL=info
```

---

## Deployment

### Docker
```bash
docker compose up -d
```

### Kubernetes
```yaml
# See deployment/k8s/ for manifests
kubectl apply -f deployment/k8s/
```

### Environment Variables for Production
```bash
DATABASE_URL=postgresql://user:pass@host/db
DATA_ROOT=/mnt/shared-storage/data
ARXIV_MAX_RESULTS=20
GEMINI_API_KEY=your_key_here
LOG_LEVEL=info
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      FastAPI Server                      │
├─────────────────────────────────────────────────────────┤
│  Routers:                                                │
│  ├─ Sessions   → Create/manage chat contexts            │
│  ├─ Documents  → Upload PDFs, fetch from arXiv          │
│  ├─ Messages   → Query knowledge graph (REST/SSE)       │
│  └─ Papers     → Search arXiv globally                  │
├─────────────────────────────────────────────────────────┤
│  Services:                                               │
│  └─ GraphRAG Service → nano-graphrag wrapper            │
├─────────────────────────────────────────────────────────┤
│  Database (SQLite/PostgreSQL):                          │
│  ├─ sessions      → Session metadata                    │
│  ├─ documents     → Document metadata & status          │
│  └─ messages      → Chat history                        │
├─────────────────────────────────────────────────────────┤
│  Filesystem (/data):                                     │
│  └─ sessions/                                            │
│     └─ {session_id}/                                     │
│        ├─ graph/     → Knowledge graph data             │
│        └─ uploads/   → Original PDFs                     │
└─────────────────────────────────────────────────────────┘
```

---

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License - see LICENSE file for details

---

## Credits

- **nano-graphrag** - Knowledge graph construction
- **FastAPI** - Web framework
- **arXiv API** - Academic paper access
- **Team DASH** - Development team

---

## Support & Issues

- **Issues:** [GitHub Issues](https://github.com/ECE496-Team-DASH/project-prometheus/issues)
- **Discussions:** [GitHub Discussions](https://github.com/ECE496-Team-DASH/project-prometheus/discussions)
- **Documentation:** This README, API_EXAMPLES.md, API_REFERENCE.md
- **Interactive Docs:** http://localhost:8000/docs

---

**Version:** 1.0.0  
**Last Updated:** October 31, 2025  
**Repository:** [project-prometheus](https://github.com/ECE496-Team-DASH/project-prometheus)
