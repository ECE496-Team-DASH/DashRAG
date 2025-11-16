
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as DBSession
from pathlib import Path
import shutil, tempfile

from ..db import SessionLocal
from ..models import Session as SessionModel
from ..config import settings

router = APIRouter(
    prefix="/sessions", 
    tags=["sessions"],
    responses={404: {"description": "Session not found"}}
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _session_root(sid: int) -> Path:
    return settings.data_root / "sessions" / str(sid)

@router.post(
    "", 
    response_model=dict,
    status_code=201,
    summary="Create a new session",
    description="""
    Create a new chat session with its own isolated knowledge graph.
    
    Each session maintains:
    - Independent knowledge graph stored in filesystem
    - Separate document collection
    - Isolated chat history
    
    **Example request:**
    ```json
    {
        "title": "Healthcare LLMs Research"
    }
    ```
    
    **Returns:** Session object with generated ID
    """,
    responses={
        201: {
            "description": "Session created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "title": "Healthcare LLMs Research",
                        "settings": {},
                        "stats": {"doc_count": 0}
                    }
                }
            }
        }
    }
)
def create_session(payload: dict, db: DBSession = Depends(get_db)):
    """Create a new session with optional title"""
    title = payload.get("title") or "New Session"
    s = SessionModel(title=title, graph_dir=str(_session_root("tmp") / "graph"))
    db.add(s); db.commit(); db.refresh(s)
    s.graph_dir = str(_session_root(s.id) / "graph")
    db.commit(); db.refresh(s)
    Path(s.graph_dir).mkdir(parents=True, exist_ok=True)
    (_session_root(s.id) / "uploads").mkdir(parents=True, exist_ok=True)
    return {"id": s.id, "title": s.title, "settings": s.settings, "stats": {"doc_count": 0}}

@router.get(
    "", 
    response_model=list[dict],
    summary="List all sessions",
    description="""
    Retrieve all chat sessions, ordered by creation date (newest first).
    
    **Use case:** Display session history in UI
    
    **Returns:** Array of session summaries
    """,
    responses={
        200: {
            "description": "List of sessions",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "title": "Healthcare LLMs Research",
                            "settings": {}
                        },
                        {
                            "id": 2,
                            "title": "Climate Change Papers",
                            "settings": {}
                        }
                    ]
                }
            }
        }
    }
)
def list_sessions(db: DBSession = Depends(get_db)):
    """Get all sessions ordered by creation date"""
    rows = db.query(SessionModel).order_by(SessionModel.created_at.desc()).all()
    return [{"id": r.id, "title": r.title, "settings": r.settings} for r in rows]

@router.get(
    "/detail", 
    response_model=dict,
    summary="Get session details",
    description="""
    Retrieve detailed information about a specific session.
    
    **Query parameters:**
    - `sid`: Session ID (integer)
    
    **Returns:** Session object with stats about the knowledge graph
    """,
    responses={
        200: {
            "description": "Session details",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "title": "Healthcare LLMs Research",
                        "settings": {},
                        "stats": {"graph_exists": True}
                    }
                }
            }
        },
        404: {"description": "Session not found"}
    }
)
def get_session(sid: int = Query(..., description="Session ID"), db: DBSession = Depends(get_db)):
    """Get details for a specific session"""
    s = db.get(SessionModel, sid)
    if not s:
        raise HTTPException(404, "Session not found")
    graph_dir = Path(s.graph_dir)
    stats = {"graph_exists": graph_dir.exists()}
    return {"id": s.id, "title": s.title, "settings": s.settings, "stats": stats}

@router.delete(
    "", 
    response_model=dict,
    summary="Delete a session",
    description="""
    Permanently delete a session and all associated data:
    - Knowledge graph files
    - Uploaded PDFs
    - Chat history
    - Database records
    
    **Warning:** This action cannot be undone. Consider using `/sessions/export?sid=...` first.
    
    **Query parameters:**
    - `sid`: Session ID to delete
    """,
    responses={
        200: {
            "description": "Session deleted successfully",
            "content": {
                "application/json": {
                    "example": {"ok": True}
                }
            }
        },
        404: {"description": "Session not found"}
    }
)
def delete_session(sid: int = Query(..., description="Session ID"), db: DBSession = Depends(get_db)):
    """Delete a session and all its data"""
    s = db.get(SessionModel, sid)
    if not s:
        raise HTTPException(404, "Session not found")
    base = Path(s.graph_dir).parent
    try:
        shutil.rmtree(base, ignore_errors=True)
    except Exception:
        pass
    db.delete(s); db.commit()
    return {"ok": True}

@router.get(
    "/export",
    summary="Export session as ZIP",
    description="""
    Download all session data as a ZIP archive.
    
    **ZIP contents:**
    - `graph/` - Knowledge graph data (entities, relationships, embeddings)
    - `uploads/` - Original PDF files
    
    **Use cases:**
    - Backup before deletion
    - Share research with collaborators
    - Migrate to another instance
    
    **Query parameters:**
    - `sid`: Session ID to export
    
    **Returns:** ZIP file download
    """,
    responses={
        200: {
            "description": "ZIP file download",
            "content": {"application/zip": {}}
        },
        404: {"description": "Session not found or directory missing"}
    }
)
def export_session(sid: int = Query(..., description="Session ID"), db: DBSession = Depends(get_db)):
    """Export session data as a ZIP file"""
    s = db.get(SessionModel, sid)
    if not s:
        raise HTTPException(404, "Session not found")
    base = _session_root(sid)
    if not base.exists():
        raise HTTPException(404, "Session directory missing")
    tmp_dir = settings.data_root / "exports"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    zip_base = tmp_dir / str(sid)
    zip_path = shutil.make_archive(str(zip_base), "zip", root_dir=base)
    return FileResponse(zip_path, filename=f"session_{sid}.zip", media_type="application/zip")
