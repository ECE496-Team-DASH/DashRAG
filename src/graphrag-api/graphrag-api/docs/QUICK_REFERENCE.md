# DashRAG API Quick Reference

One-page reference for the most common operations.

---

## 🚀 Quick Start

```bash
# Start server
uvicorn app.main:app --reload

# Interactive docs
http://localhost:8000/docs
```

---

## 📋 Common Workflows

### Create Session → Upload PDF → Query

```bash
# 1. Create session
SESSION_ID=$(curl -s -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"title":"My Research"}' | jq -r '.id')

# 2. Upload PDF
curl -X POST \
  "http://localhost:8000/documents/upload?sid=$SESSION_ID" \
  -F "file=@paper.pdf"

# 3. Query
curl -X POST \
  "http://localhost:8000/messages?sid=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Summarize the main findings",
    "mode": "global"
  }'
```

### Search arXiv → Add Papers → Query

```bash
# 1. Search arXiv
curl "http://localhost:8000/papers/search?query=transformers&max_results=3"

# 2. Add paper
curl -X POST \
  "http://localhost:8000/documents/add-arxiv?sid=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"arxiv_id":"1706.03762"}'

# 3. Query
curl -X POST \
  "http://localhost:8000/messages?sid=$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"content":"Compare methods","mode":"global"}'
```

---

## 🔑 Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/sessions` | POST | Create session |
| `/sessions` | GET | List sessions |
| `/sessions/detail?sid=...` | GET | Get session |
| `/sessions?sid=...` | DELETE | Delete session |
| `/sessions/export?sid=...` | GET | Export ZIP |
| `/documents?sid=...` | GET | List docs |
| `/documents/upload?sid=...` | POST | Upload PDF |
| `/documents/add-arxiv?sid=...` | POST | Add arXiv |
| `/messages?sid=...` | GET | Get history |
| `/messages?sid=...` | POST | Query (REST) |
| `/messages/stream?sid=...` | POST | Query (SSE) |
| `/papers/search` | GET | Search arXiv |

---

## 🎯 Query Modes

| Mode | Speed | Best For | top_k |
|------|-------|----------|-------|
| `local` | Fast | Specific questions | 10 |
| `global` | Slow | Cross-doc synthesis | 20 |
| `naive` | Fastest | Quick lookups | 10 |

---

## 📊 Document Status

```
pending → downloading → inserting → ready
                                 ↘ error
```

- **pending**: Created, not processed
- **downloading**: Fetching from arXiv
- **inserting**: Building graph
- **ready**: Can query
- **error**: Failed (check logs)

---

## 🐍 Python Quick Examples

### Create & Query
```python
import requests

BASE = "http://localhost:8000"

# Create
session = requests.post(f"{BASE}/sessions", 
                       json={"title": "Research"}).json()
sid = session["id"]

# Upload
with open("paper.pdf", "rb") as f:
    requests.post(f"{BASE}/documents/upload?sid={sid}",
                 files={"file": f})

# Query
response = requests.post(f"{BASE}/messages",
                        params={"sid": sid},
                        json={"content": "Summarize", 
                              "mode": "global"})
print(response.json()["message"]["content"]["text"])
```

### Stream Response
```python
import requests, json

response = requests.post(
    f"{BASE}/messages/stream",
    params={"sid": sid},
    json={"content": "Explain findings", "mode": "global"},
    stream=True
)

for line in response.iter_lines():
    if line.startswith(b"data: "):
        data = json.loads(line[6:])
        if data["type"] == "token":
            print(data["text"], end="", flush=True)
```

---

## 🌐 JavaScript Quick Examples

### Fetch API
```javascript
const BASE = "http://localhost:8000";

// Create session
const session = await fetch(`${BASE}/sessions`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ title: 'Research' })
}).then(r => r.json());

// Query
const response = await fetch(`${BASE}/sessions/${session.id}/messages`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ 
    content: 'Summarize', 
    mode: 'global' 
  })
}).then(r => r.json());

console.log(response.message.content.text);
```

### EventSource (Streaming)
```javascript
const eventSource = new EventSource(
  `${BASE}/sessions/${sid}/messages/stream`
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

## ⚠️ Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 404 Session not found | Invalid session ID | Verify session exists |
| 400 No ready documents | No docs processed | Add & wait for docs |
| 400 Only PDF supported | Wrong file type | Upload PDF only |
| 500 Query failed | Graph error | Check logs |

---

## 🔧 Environment Variables

```bash
# Required: Choose one LLM provider
GEMINI_API_KEY=your_key
# OR
OPENAI_API_KEY=your_key
# OR
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://...

# Optional
DATABASE_URL=sqlite:///./data/app.db
DATA_ROOT=./data
ARXIV_MAX_RESULTS=20
```

---

## 📈 Response Times (Typical)

| Operation | Duration |
|-----------|----------|
| Create session | < 100ms |
| Upload PDF (10 pages) | 5-15s |
| Add arXiv paper | 10-30s |
| Query (local) | 2-5s |
| Query (global) | 5-10s |
| Export session | 1-3s |

---

## 💡 Best Practices

✅ **DO:**
- Store session IDs
- Poll document status before querying
- Use `local` mode for specific questions
- Use `global` mode for summaries
- Export sessions before deleting
- Handle errors gracefully

❌ **DON'T:**
- Query without ready documents
- Upload non-PDF files
- Delete without exporting
- Ignore error responses
- Use very large PDFs (>50MB)

---

## 🎨 Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request |
| 404 | Not found |
| 500 | Server error |

---

## 📚 Documentation

- **README.md** - Getting started
- **API_EXAMPLES.md** - Code examples
- **API_REFERENCE.md** - Complete reference
- **/docs** - Interactive Swagger UI
- **/redoc** - Alternative docs
- **/openapi.json** - OpenAPI spec

---

## 🔍 Debugging

```python
# Check health
requests.get("http://localhost:8000/healthz").json()

# List sessions
requests.get("http://localhost:8000/sessions").json()

# Check doc status
requests.get(f"http://localhost:8000/documents", params={"sid": sid}).json()

# View chat history
requests.get(f"http://localhost:8000/messages", params={"sid": sid}).json()
```

---

## 🚦 Test Script

```bash
#!/bin/bash
BASE="http://localhost:8000"

# Health check
curl $BASE/healthz

# Create session
SID=$(curl -s -X POST $BASE/sessions \
  -H "Content-Type: application/json" \
  -d '{"title":"Test"}' | jq -r '.id')
echo "Session: $SID"

# Add paper
curl -X POST "$BASE/documents/add-arxiv?sid=$SID" \
  -H "Content-Type: application/json" \
  -d '{"arxiv_id":"1706.03762"}'

# Wait a bit
sleep 20

# Query
curl -X POST "$BASE/messages?sid=$SID" \
  -H "Content-Type: application/json" \
  -d '{"content":"Summarize","mode":"local"}'

# Cleanup
curl -X DELETE "$BASE/sessions?sid=$SID"
```

---

**Print this for quick reference during development!**
