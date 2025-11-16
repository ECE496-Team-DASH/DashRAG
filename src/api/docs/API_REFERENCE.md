# DashRAG API Reference

Complete API reference with detailed schemas and parameter descriptions.

## Base URL

```
Development: http://localhost:8000
Production: https://your-domain.com
```

## Authentication

**Current:** None (open API)
**Production recommendation:** Add JWT or API key middleware

---

## Data Models

### Session

Represents an isolated chat context with its own knowledge graph.

```json
{
  "id": 1,
  "title": "string",
  "settings": {},
  "stats": {
    "doc_count": 0,
    "graph_exists": true
  }
}
```

**Fields:**
- `id` (integer, read-only): Unique session identifier (auto-incrementing)
- `title` (string): Human-readable session name
- `settings` (object): Custom session configuration (future use)
- `stats` (object, read-only): Computed statistics about the session

---

### Document

Represents a PDF document added to a session's knowledge graph.

```json
{
  "id": 1,
  "session_id": 1,
  "title": "paper_name.pdf",
  "source_type": "upload",
  "status": "ready",
  "arxiv_id": null,
  "authors": ["Author 1", "Author 2"],
  "published_at": "2024-01-15",
  "pages": 15,
  "created_at": "2024-10-31T10:30:00Z"
}
```

**Fields:**
- `id` (integer, read-only): Unique document identifier (auto-incrementing)
- `session_id` (integer): Parent session ID
- `title` (string): Document title
- `source_type` (enum): `"upload"` or `"arxiv"`
- `status` (enum): Document processing status
  - `"pending"`: Created but not processed
  - `"downloading"`: Fetching from arXiv
  - `"inserting"`: Building knowledge graph
  - `"ready"`: Available for querying
  - `"error"`: Processing failed
- `arxiv_id` (string, nullable): arXiv identifier (e.g., "1706.03762")
- `authors` (array[string], nullable): List of author names
- `published_at` (string, nullable): Publication date (ISO 8601)
- `pages` (integer, nullable): Number of pages
- `created_at` (string, read-only): Creation timestamp (ISO 8601)

---

### Message

Represents a message in the chat history.

```json
{
  "id": 1,
  "session_id": 1,
  "role": "user",
  "content": {
    "text": "What are the main findings?"
  },
  "token_usage": {
    "prompt": 1024,
    "completion": 512,
    "total": 1536
  },
  "created_at": "2024-10-31T10:35:00Z"
}
```

**Fields:**
- `id` (integer, read-only): Unique message identifier (auto-incrementing)
- `session_id` (integer): Parent session ID
- `role` (enum): Message sender
  - `"user"`: User question/prompt
  - `"assistant"`: AI-generated response
  - `"tool"`: Tool/function result (future)
  - `"system"`: System message (future)
- `content` (object): Message content
  - `text` (string): Message text
  - Additional fields may be added for citations, metadata
- `token_usage` (object, nullable): LLM token consumption
  - `prompt` (integer): Input tokens
  - `completion` (integer): Output tokens
  - `total` (integer): Total tokens
- `created_at` (string, read-only): Creation timestamp (ISO 8601)

---

### Paper (arXiv)

Represents an arXiv paper from search results.

```json
{
  "arxiv_id": "1706.03762",
  "title": "Attention Is All You Need",
  "authors": ["Ashish Vaswani", "Noam Shazeer"],
  "abstract": "The dominant sequence transduction models...",
  "published_at": "2017-06-12",
  "pdf_url": "http://arxiv.org/pdf/1706.03762"
}
```

**Fields:**
- `arxiv_id` (string): arXiv identifier
- `title` (string): Paper title
- `authors` (array[string]): Author names
- `abstract` (string): Paper abstract
- `published_at` (string): Publication date
- `pdf_url` (string): Direct PDF download URL

---

## Endpoints

### Health

#### `GET /healthz`

Check API health and filesystem status.

**Parameters:** None

**Response 200:**
```json
{
  "ok": true,
  "data_root": "/app/data",
  "can_write_data_root": true,
  "free_space_mb": 15360
}
```

**Use case:** Health checks, monitoring, pre-deployment validation

---

### Sessions

#### `POST /sessions`

Create a new session.

**Request Body:**
```json
{
  "title": "string"  // Optional, defaults to "New Session"
}
```

**Response 201:**
```json
{
  "id": "sess_xxxxxxxxxxxx",
  "title": "string",
  "settings": {},
  "stats": {
    "doc_count": 0
  }
}
```

**Errors:**
- 500: Database or filesystem error

---

#### `GET /sessions`

List all sessions.

**Parameters:** None

**Response 200:**
```json
[
  {
    "id": "sess_xxxxxxxxxxxx",
    "title": "string",
    "settings": {}
  }
]
```

**Note:** Sessions are ordered by creation date (newest first)

---

#### `GET /sessions/detail?sid={sid}`

Get session details.

**Query Parameters:**
- `sid` (string, required): Session ID

**Response 200:**
```json
{
  "id": "sess_xxxxxxxxxxxx",
  "title": "string",
  "settings": {},
  "stats": {
    "graph_exists": true
  }
}
```

**Errors:**
- 404: Session not found

---

#### `DELETE /sessions?sid={sid}`

Delete a session and all associated data.

**Query Parameters:**
- `sid` (string, required): Session ID

**Response 200:**
```json
{
  "ok": true
}
```

**Errors:**
- 404: Session not found

**Warning:** This operation is permanent. Consider exporting first.

---

#### `GET /sessions/export?sid={sid}`

Export session as ZIP file.

**Query Parameters:**
- `sid` (string, required): Session ID

**Response 200:** ZIP file download
- `Content-Type: application/zip`
- `Content-Disposition: attachment; filename="{sid}.zip"`

**ZIP Contents:**
- `graph/` - Knowledge graph data
- `uploads/` - Original PDF files

**Errors:**
- 404: Session not found or directory missing

---

### Documents

#### `GET /documents?sid={sid}`

List documents in a session.

**Query Parameters:**
- `sid` (string, required): Session ID

**Response 200:**
```json
[
  {
    "id": "doc_xxxxxxxxxxxx",
    "title": "paper.pdf",
    "source_type": "upload",
    "status": "ready",
    "arxiv_id": null,
    "pages": 12
  }
]
```

**Errors:**
- 404: Session not found

---

#### `POST /documents/upload?sid={sid}`

Upload a PDF document.

**Query Parameters:**
- `sid` (string, required): Session ID

**Request:** Multipart form-data
- `file` (file, required): PDF file

**Response 200:**
```json
{
  "id": "doc_xxxxxxxxxxxx",
  "status": "ready",
  "title": "paper.pdf"
}
```

**Errors:**
- 400: Invalid file format (must be PDF)
- 404: Session not found
- 413: File too large
- 500: Processing error

**Processing:** Synchronous (blocks until complete)

**Typical duration:** 5-30 seconds depending on PDF size

---

#### `GET /documents/search-arxiv?sid={sid}`

Search arXiv papers (preview, doesn't add to session).

**Query Parameters:**
- `sid` (string, required): Session ID
- `query` (string, required): Search terms
- `max_results` (integer, optional): Max papers to return (default: 5)

**Response 200:**
```json
[
  {
    "arxiv_id": "1706.03762",
    "title": "Attention Is All You Need",
    "authors": ["..."],
    "abstract": "...",
    "published_at": "2017-06-12",
    "pdf_url": "http://arxiv.org/pdf/1706.03762"
  }
]
```

**Errors:**
- 404: Session not found

**Note:** This endpoint doesn't modify the session. Use `POST /documents/add-arxiv` to add papers.

---

#### `POST /documents/add-arxiv?sid={sid}`

Download and add an arXiv paper to the session.

**Query Parameters:**
- `sid` (string, required): Session ID

**Request Body:**
```json
{
  "arxiv_id": "1706.03762"  // Required
}
```

**Response 200:**
```json
{
  "id": "doc_xxxxxxxxxxxx",
  "status": "ready",
  "arxiv_id": "1706.03762"
}
```

**Errors:**
- 400: Missing or invalid arxiv_id
- 404: Session not found or arXiv paper not found
- 500: Download or processing error

**Processing:** Synchronous (blocks until complete)

**Typical duration:** 10-30 seconds (download + processing)

---

### Messages

#### `GET /messages?sid={sid}`

Get chat history for a session.

**Query Parameters:**
- `sid` (string, required): Session ID

**Response 200:**
```json
[
  {
    "id": "msg_xxxxxxxxxxxx",
    "role": "user",
    "content": {"text": "..."}
  },
  {
    "id": "msg_xxxxxxxxxxxx",
    "role": "assistant",
    "content": {"text": "..."}
  }
]
```

**Errors:**
- 404: Session not found

**Note:** Messages are ordered chronologically (oldest first)

---

#### `POST /messages?sid={sid}`

Query the knowledge graph (non-streaming).

**Query Parameters:**
- `sid` (string, required): Session ID

**Request Body:**
```json
{
  "content": "string",  // Required: user question
  "mode": "local",      // Optional: "local" | "global" | "naive"
  "top_k": 10,          // Optional: number of results (default varies by mode)
  
  // Advanced parameters (all optional):
  "level": 0,
  "response_type": "string",
  "only_need_context": false,
  "include_text_chunks_in_context": false,
  "global_max_consider_community": 100,
  "global_min_community_rating": 0,
  "naive_max_token_for_text_unit": 4000
}
```

**Query Parameter Details:**

**`mode`** (string, default: "local")
- `"local"`: Search specific text chunks
  - Best for: Targeted questions about specific topics
  - Speed: Fast
  - Default `top_k`: 60
- `"global"`: Cross-document community-based synthesis
  - Best for: Broad summaries, theme identification
  - Speed: Slower
  - Default `top_k`: 60
- `"naive"`: Simple keyword matching
  - Best for: Quick lookups
  - Speed: Fastest
  - Default `top_k`: 60

**`top_k`** (integer, default: 60)
- Number of text chunks/communities to retrieve
- Higher values = more context but slower
- Recommended ranges:
  - Local: 5-20
  - Global: 10-30
  - Naive: 5-15

**`level`** (integer, optional)
- Community hierarchy level for global mode
- 0 = most detailed, higher = more abstract

**`response_type`** (string, optional)
- Hint for response formatting
- Examples: "concise", "detailed", "bullet_points"

**`only_need_context`** (boolean, default: false)
- If true, return retrieved context without LLM generation
- Useful for debugging or custom processing

**`include_text_chunks_in_context`** (boolean, optional)
- Include source text chunks in the response
- Useful for citation/provenance

**`global_max_consider_community`** (integer, optional)
- Max number of communities to consider in global mode

**`global_min_community_rating`** (integer, optional)
- Minimum rating threshold for communities

**`naive_max_token_for_text_unit`** (integer, optional)
- Token limit per text unit in naive mode

**Response 200:**
```json
{
  "message": {
    "id": "msg_xxxxxxxxxxxx",
    "role": "assistant",
    "content": {
      "text": "Based on the knowledge graph..."
    }
  }
}
```

**Errors:**
- 400: Invalid parameters or no ready documents
- 404: Session not found
- 500: Query processing error

**Requirements:**
- Session must have at least one document with `status: "ready"`

**Typical duration:** 2-10 seconds depending on mode and complexity

---

#### `POST /messages/stream?sid={sid}`

Query with Server-Sent Events (SSE) streaming.

**Query Parameters:**
- `sid` (string, required): Session ID

**Request Body:** Same as non-streaming endpoint

**Response 200:** SSE stream
- `Content-Type: text/event-stream`

**Event Types:**

1. **Token Event** (response text):
```
data: {"type": "token", "text": "Response text here"}
```

2. **Done Event** (stream complete):
```
data: {"type": "done"}
```

3. **Error Event** (query failed):
```
data: {"type": "error", "message": "Error description"}
```

**Errors:**
- 400: Invalid parameters or no ready documents
- 404: Session not found

**Client Implementation:**

**JavaScript (EventSource):**
```javascript
const eventSource = new EventSource(url);
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Handle data.type
};
```

**Python (requests):**
```python
response = requests.post(url, json=payload, stream=True)
for line in response.iter_lines():
    if line.startswith(b'data: '):
        data = json.loads(line[6:])
        # Handle data['type']
```

---

### Papers

#### `GET /papers/search`

Search arXiv papers globally (not session-specific).

**Query Parameters:**
- `query` (string, required): Search terms
- `max_results` (integer, optional): Max results (default: 10)

**Response 200:**
```json
[
  {
    "arxiv_id": "1706.03762",
    "title": "Attention Is All You Need",
    "authors": ["..."],
    "abstract": "...",
    "published_at": "2017-06-12",
    "pdf_url": "http://arxiv.org/pdf/1706.03762"
  }
]
```

**Use case:** Browse papers before creating a session

---

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message description"
}
```

### HTTP Status Codes

- **200 OK**: Successful request
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid parameters or request body
- **404 Not Found**: Resource not found
- **413 Payload Too Large**: File upload exceeds limit
- **429 Too Many Requests**: Rate limit exceeded (if enabled)
- **500 Internal Server Error**: Server error

### Common Error Messages

**400 Errors:**
```json
{"detail": "Only PDF files are supported"}
{"detail": "content must be a string"}
{"detail": "arxiv_id is required"}
{"detail": "Add at least one ready document before querying"}
```

**404 Errors:**
```json
{"detail": "Session not found"}
{"detail": "Session directory missing"}
```

**500 Errors:**
```json
{"detail": "Query processing failed: [reason]"}
{"detail": "Failed to extract text from PDF"}
```

---

## Rate Limits

**Current:** No rate limiting (open API)

**Production Recommendations:**
- 10 requests/second per IP for reads
- 2 requests/second per IP for document uploads
- 1 request/second per IP for queries

Implement rate limiting middleware before production deployment.

---

## File Size Limits

**PDF Uploads:**
- Recommended: < 20 MB per file
- Maximum: Configured by server (default: 100 MB)

**arXiv Downloads:**
- Typically: 1-10 MB per paper
- Occasional large papers: up to 50 MB

---

## Pagination

**Current:** No pagination (all results returned)

**Future:** Endpoints will support:
```
?limit=20&offset=0
```
or
```
?limit=20&cursor=base64_encoded_cursor
```

---

## Webhooks

**Current:** Not supported

**Future:** Planned support for:
- Document processing completion
- Query completion (for async mode)
- Session events

---

## Versioning

**Current:** v1 (implicit)

**Future:** Version will be included in URL:
```
/v1/sessions
/v2/sessions
```

Breaking changes will be introduced in new versions only.

---

## OpenAPI Specification

Access the full OpenAPI 3.0 specification:

```
GET /openapi.json
```

Import into tools like Postman, Insomnia, or code generators.

---

## SDK Support

**Official SDKs:** None (REST API only)

**Community SDKs:** Welcome! Follow OpenAPI spec.

**Code Generation:** Use OpenAPI Generator with `/openapi.json`

---

## WebSocket Support

**Current:** Not supported (use SSE for streaming)

**Future:** May add WebSocket support for bi-directional communication

---

## GraphQL Support

**Current:** REST only

**Future:** No plans for GraphQL. REST + SSE is sufficient.

---

## Testing

### Test Endpoints

Use the Swagger UI for interactive testing:
```
http://localhost:8000/docs
```

### Sample Test Session

```bash
# 1. Create session
SESSION_ID=$(curl -s -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"title":"Test"}' | jq -r '.id')

# 2. Add test paper
curl -X POST \
  http://localhost:8000/sessions/$SESSION_ID/documents/add-arxiv \
  -H "Content-Type: application/json" \
  -d '{"arxiv_id":"1706.03762"}'

# 3. Query
curl -X POST \
  http://localhost:8000/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"content":"Summarize this paper","mode":"local"}'

# 4. Cleanup
curl -X DELETE http://localhost:8000/sessions/$SESSION_ID
```

---

## Support

- **Documentation:** [README.md](./README.md), [API_EXAMPLES.md](./API_EXAMPLES.md)
- **Interactive Docs:** http://localhost:8000/docs
- **Issues:** GitHub repository issue tracker
- **Email:** team@dashrag.example.com

---

**Last Updated:** 2025-10-31
