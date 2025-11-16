
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession
from typing import AsyncGenerator
from pathlib import Path
import asyncio, json

from ..db import SessionLocal
from ..models import Session as SessionModel, Document, Message, Role, DocStatus
from ..services.graphrag_service import DashRAGService
from ..services.background_tasks import process_message_query
from ..config import settings

router = APIRouter(
    prefix="/messages", 
    tags=["messages"],
    responses={404: {"description": "Session not found"}}
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _graph_dir(sid: int) -> Path:
    return settings.data_root / "sessions" / str(sid) / "graph"

@router.get(
    "", 
    response_model=list[dict],
    summary="Get chat history",
    description="""
    Retrieve all messages in a session's chat history.
    
    **Message roles:**
    - `user` - User questions/prompts
    - `assistant` - AI-generated responses
    - `tool` - Tool/function call results (future use)
    - `system` - System messages (future use)
    
    **Query parameters:**
    - `sid`: Session ID
    
    **Returns:** Array of messages in chronological order
    """,
    responses={
        200: {
            "description": "Chat history",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "role": "user",
                            "content": {"text": "What are the key innovations in transformers?"}
                        },
                        {
                            "id": 2,
                            "role": "assistant",
                            "content": {"text": "Based on the papers, the key innovations include..."}
                        }
                    ]
                }
            }
        }
    }
)
def list_messages(sid: int = Query(..., description="Session ID"), db: DBSession = Depends(get_db)):
    """Get all messages in a session"""
    sess = db.get(SessionModel, sid)
    if not sess:
        raise HTTPException(404, "Session not found")
    rows = db.query(Message).filter(Message.session_id==sid).order_by(Message.created_at.asc()).all()
    return [{"id": m.id, "role": m.role.value, "content": m.content} for m in rows]

@router.post(
    "", 
    response_model=dict,
    status_code=202,
    summary="Query knowledge graph (non-streaming)",
    description="""
    Query the session's knowledge graph asynchronously and get an AI-generated response.
    
    **Process:**
    1. User message is created immediately
    2. 202 Accepted response returned with message ID
    3. Background processing:
       - Query executed against knowledge graph
       - AI generates response
       - Assistant message created with answer
    
    **Use GET /messages?sid={sid} to retrieve the full conversation including the AI response**
    
    **Request body:**
    ```json
    {
        "content": "What are the main contributions?",
        "mode": "global",
        "top_k": 10
    }
    ```
    
    **Query modes:**
    - **`local`** (default): Search specific text chunks
      - Fast, precise for targeted questions
      - Best for: "What does paper X say about Y?"
    
    - **`global`**: Cross-document synthesis via community detection
      - Slower, comprehensive for broad questions
      - Best for: "Summarize themes across all papers"
    
    - **`naive`**: Simple keyword matching
      - Fastest, least sophisticated
      - Best for: Quick lookups
    
    **Optional parameters:**
    - `top_k` (int): Number of results to retrieve (default: 60)
    - `level` (int): Community hierarchy level for global mode
    - `response_type` (str): Response formatting hint
    - `only_need_context` (bool): Return context without LLM generation
    - `include_text_chunks_in_context` (bool): Include source chunks
    - `global_max_consider_community` (int): Max communities in global mode
    - `global_min_community_rating` (int): Min rating threshold
    - `naive_max_token_for_text_unit` (int): Token limit for naive mode
    
    **Query parameters:**
    - `sid`: Session ID
    
    **Requirements:** Session must have at least one document with status `ready`
    """,
    responses={
        202: {
            "description": "Query accepted for processing",
            "content": {
                "application/json": {
                    "example": {
                        "message_id": 1,
                        "status": "processing"
                    }
                }
            }
        },
        400: {"description": "No ready documents or invalid parameters"},
        404: {"description": "Session not found"}
    }
)
async def create_message(
    background_tasks: BackgroundTasks,
    sid: int = Query(..., description="Session ID"),
    payload: dict = None,
    db: DBSession = Depends(get_db)
):
    """Query the knowledge graph in the background"""
    sess = db.get(SessionModel, sid)
    if not sess:
        raise HTTPException(404, "Session not found")

    has_ready = db.query(Document).filter(Document.session_id==sid, Document.status==DocStatus.ready).count() > 0
    if not has_ready:
        raise HTTPException(400, "Add at least one ready document before querying")

    prompt = payload.get("content")
    if not prompt or not isinstance(prompt, str):
        raise HTTPException(400, "content must be a string")

    # Create user message immediately
    m_user = Message(session_id=sid, role=Role.user, content={"text": prompt})
    db.add(m_user)
    db.commit()
    db.refresh(m_user)

    # Extract query parameters
    qp_kwargs = {k: payload.get(k) for k in [
        "mode", "top_k", "level", "response_type", "only_need_context",
        "include_text_chunks_in_context", "global_max_consider_community",
        "global_min_community_rating", "naive_max_token_for_text_unit"
    ]}

    # Schedule background processing
    background_tasks.add_task(
        process_message_query,
        message_id=m_user.id,
        session_id=sid,
        prompt=prompt,
        graph_dir=_graph_dir(sid),
        qp_kwargs=qp_kwargs
    )

    return {"message_id": m_user.id, "status": "processing"}

@router.post(
    "/stream",
    summary="Query with streaming response (SSE)",
    description="""
    Query the knowledge graph with Server-Sent Events (SSE) streaming.
    
    **Same parameters as non-streaming endpoint**, but response is streamed in real-time.
    
    **SSE Event types:**
    
    1. **Token event** (response text):
    ```
    data: {"type": "token", "text": "Based on the papers..."}
    ```
    
    2. **Done event** (end of stream):
    ```
    data: {"type": "done"}
    ```
    
    3. **Error event** (if query fails):
    ```
    data: {"type": "error", "message": "Error description"}
    ```
    
    **Use case:** Real-time UI updates as the AI generates the response
    
    **Content-Type:** `text/event-stream`
    
    **Example (JavaScript):**
    ```javascript
    const eventSource = new EventSource('/messages/stream?sid=sess_abc');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'token') {
            console.log(data.text);
        } else if (data.type === 'done') {
            eventSource.close();
        }
    };
    ```
    
    **Example (Python):**
    ```python
    import requests
    import json
    
    response = requests.post(
        'http://localhost:8000/messages/stream?sid=sess_abc',
        json={'content': 'Summarize papers', 'mode': 'global'},
        stream=True
    )
    
    for line in response.iter_lines():
        if line.startswith(b'data: '):
            data = json.loads(line[6:])
            if data['type'] == 'token':
                print(data['text'], end='', flush=True)
    ```
    """,
    responses={
        200: {
            "description": "SSE stream of response",
            "content": {"text/event-stream": {}}
        },
        400: {"description": "No ready documents or invalid parameters"},
        404: {"description": "Session not found"}
    }
)
async def create_message_stream(sid: int = Query(..., description="Session ID"), payload: dict = None, db: DBSession = Depends(get_db)):
    """Query with SSE streaming response"""
    sess = db.get(SessionModel, sid)
    if not sess:
        raise HTTPException(404, "Session not found")

    has_ready = db.query(Document).filter(Document.session_id==sid, Document.status==DocStatus.ready).count() > 0
    if not has_ready:
        raise HTTPException(400, "Add at least one ready document before querying")

    prompt = payload.get("content")
    if not prompt or not isinstance(prompt, str):
        raise HTTPException(400, "content must be a string")

    m_user = Message(session_id=sid, role=Role.user, content={"text": prompt})
    db.add(m_user); db.commit(); db.refresh(m_user)

    qp_kwargs = {k: payload.get(k) for k in [
        "mode", "top_k", "level", "response_type", "only_need_context",
        "include_text_chunks_in_context", "global_max_consider_community",
        "global_min_community_rating", "naive_max_token_for_text_unit"
    ]}

    rag = DashRAGService(_graph_dir(sid))
    try:
        answer = await rag.query(prompt, **{k:v for k,v in qp_kwargs.items() if v is not None})
    except ValueError as e:
        # User-friendly error messages
        async def err_stream():
            payload = {"type": "error", "message": str(e)}
            yield ("data: " + json.dumps(payload) + "\n\n").encode("utf-8")
        return StreamingResponse(err_stream(), media_type="text/event-stream")
    except Exception as e:
        # Internal errors
        async def err_stream():
            payload = {"type": "error", "message": f"Query failed: {str(e)}"}
            yield ("data: " + json.dumps(payload) + "\n\n").encode("utf-8")
        return StreamingResponse(err_stream(), media_type="text/event-stream")

    # Persist assistant message before streaming
    m_asst = Message(session_id=sid, role=Role.assistant, content={"text": answer})
    db.add(m_asst); db.commit(); db.refresh(m_asst)

    async def event_stream() -> AsyncGenerator[bytes, None]:
        yield f"data: {json.dumps({'type': 'token', 'text': answer})}\n\n".encode("utf-8")
        yield f"data: {json.dumps({'type': 'done'})}\n\n".encode("utf-8")

    return StreamingResponse(event_stream(), media_type="text/event-stream")
