
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session as DBSession
from pathlib import Path
import logging
import traceback

from ..db import SessionLocal
from ..models import Session as SessionModel, Document, DocSource, DocStatus
from ..utils.pdf_utils import extract_text
from ..utils.arxiv_utils import search_arxiv, download_pdf
from ..services.graphrag_service import DashRAGService
from ..services.background_tasks import process_uploaded_document, process_arxiv_document
from ..utils.locks import session_lock
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents", 
    tags=["documents"],
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
def _uploads_dir(sid: int) -> Path:
    return _session_root(sid) / "uploads"
def _lock_file(sid: int) -> Path:
    return _session_root(sid) / ".lock"
def _graph_dir(sid: int) -> Path:
    return _session_root(sid) / "graph"

@router.get(
    "", 
    response_model=list[dict],
    summary="List documents in session",
    description="""
    Retrieve all documents added to a session.
    
    **Document status values:**
    - `pending` - Created but not yet processed
    - `downloading` - Fetching from arXiv
    - `inserting` - Extracting text and building knowledge graph
    - `ready` - Available for querying
    - `error` - Processing failed (check logs)
    
    **Query parameters:**
    - `sid`: Session ID
    
    **Returns:** Array of document summaries with metadata
    """,
    responses={
        200: {
            "description": "List of documents",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "title": "transformer_paper.pdf",
                            "source_type": "upload",
                            "status": "ready",
                            "arxiv_id": None,
                            "pages": 15
                        },
                        {
                            "id": 2,
                            "title": "Attention Is All You Need",
                            "source_type": "arxiv",
                            "status": "ready",
                            "arxiv_id": "1706.03762",
                            "pages": 12
                        }
                    ]
                }
            }
        }
    }
)
def list_docs(sid: int = Query(..., description="Session ID"), db: DBSession = Depends(get_db)):
    """List all documents in a session"""
    if not db.get(SessionModel, sid):
        raise HTTPException(404, "Session not found")
    docs = db.query(Document).filter(Document.session_id==sid).order_by(Document.created_at.desc()).all()
    return [{
        "id": d.id, "title": d.title, "source_type": d.source_type.value,
        "status": d.status.value, "arxiv_id": d.arxiv_id, "pages": d.pages
    } for d in docs]

@router.post(
    "/upload", 
    response_model=dict,
    status_code=202,
    summary="Upload PDF document",
    description="""
    Upload a PDF file for asynchronous processing and knowledge graph insertion.
    
    **Process:**
    1. File is saved to session's uploads directory
    2. Document record created with status `inserting`
    3. 202 Accepted response returned immediately
    4. Background processing:
       - Text extracted from PDF
       - Entities and relationships extracted
       - Knowledge graph updated
       - Status changes: `inserting` → `ready` (or `error`)
    
    **Request:** Multipart form-data with `file` field
    
    **Accepts:** PDF files only (`.pdf` extension)
    
    **Query parameters:**
    - `sid`: Session ID
    
    **Use GET /documents?sid={sid} to check document status**
    """,
    responses={
        202: {
            "description": "Document accepted for processing",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "status": "inserting",
                        "title": "my_research_paper.pdf"
                    }
                }
            }
        },
        400: {"description": "Invalid file format (must be PDF)"},
        404: {"description": "Session not found"}
    }
)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    sid: int = Query(..., description="Session ID"),
    file: UploadFile = File(...),
    db: DBSession = Depends(get_db)
):
    """Upload a PDF and process it in the background"""
    logger.info(f"Uploading PDF '{file.filename}' to session {sid}")
    sess = db.get(SessionModel, sid)
    if not sess:
        raise HTTPException(404, "Session not found")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    uploads = _uploads_dir(sid)
    uploads.mkdir(parents=True, exist_ok=True)
    doc = Document(session_id=sid, source_type=DocSource.upload, status=DocStatus.inserting, title=file.filename)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        pdf_path = uploads / f"{doc.id}.pdf"
        data = await file.read()
        pdf_path.write_bytes(data)
        doc.local_pdf_path = str(pdf_path)
        db.commit()
        logger.info(f"PDF saved to {pdf_path}, scheduling background processing")
        
        # Schedule background processing
        background_tasks.add_task(
            process_uploaded_document,
            doc_id=doc.id,
            session_id=sid,
            pdf_path=pdf_path,
            graph_dir=_graph_dir(sid),
            lock_file=_lock_file(sid)
        )
        
        return {"id": doc.id, "status": doc.status.value, "title": doc.title}
        
    except Exception as e:
        error_msg = f"Failed to save PDF: {str(e)}"
        logger.error(error_msg, exc_info=True)
        doc.status = DocStatus.error
        doc.insert_log = f"{error_msg}\n\nTraceback:\n{traceback.format_exc()}"
        db.commit()
        raise HTTPException(500, error_msg)

@router.get(
    "/search-arxiv", 
    response_model=list[dict],
    summary="Search arXiv papers",
    description="""
    Search arXiv without adding documents to the session (preview mode).
    
    **Use case:** Let users browse and select papers before adding them.
    
    **Query parameters:**
    - `query` (required): Search terms (e.g., "transformer attention mechanism")
    - `max_results` (optional, default=5): Maximum papers to return (capped by server config)
    
    **Returns:** Array of arXiv paper metadata (no side effects)
    
    **Next step:** Use `POST /documents/add-arxiv?sid=...` to add selected papers
    """,
    responses={
        200: {
            "description": "Search results from arXiv",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "arxiv_id": "1706.03762",
                            "title": "Attention Is All You Need",
                            "authors": ["Ashish Vaswani", "Noam Shazeer"],
                            "abstract": "The dominant sequence transduction models...",
                            "published_at": "2017-06-12",
                            "pdf_url": "http://arxiv.org/pdf/1706.03762"
                        }
                    ]
                }
            }
        }
    }
)
def preview_arxiv(sid: int = Query(..., description="Session ID"), query: str = Query(..., description="Search query"), max_results: int = Query(5, description="Maximum number of results"), db: DBSession = Depends(get_db)):
    """Preview arXiv search results without adding documents"""
    if not db.get(SessionModel, sid):
        raise HTTPException(404, "Session not found")
    max_results = min(max_results, settings.arxiv_max_results)
    return search_arxiv(query, max_results=max_results)

@router.post(
    "/add-arxiv", 
    response_model=dict,
    status_code=202,
    summary="Add arXiv paper to session",
    description="""
    Download and process an arXiv paper asynchronously.
    
    **Process:**
    1. Document record created with status `downloading`
    2. 202 Accepted response returned immediately
    3. Background processing:
       - Download PDF from arXiv
       - Extract text
       - Build knowledge graph
       - Status transitions: `downloading` → `inserting` → `ready` (or `error`)
    
    **Request body:**
    ```json
    {
        "arxiv_id": "1706.03762"
    }
    ```
    
    **Query parameters:**
    - `sid`: Session ID
    
    **arXiv ID formats accepted:**
    - `1706.03762` (new format)
    - `cs/0703001` (old format)
    
    **Use GET /documents?sid={sid} to check document status**
    """,
    responses={
        202: {
            "description": "Paper accepted for processing",
            "content": {
                "application/json": {
                    "example": {
                        "id": 2,
                        "status": "downloading",
                        "arxiv_id": "1706.03762"
                    }
                }
            }
        },
        400: {"description": "Missing or invalid arxiv_id"},
        404: {"description": "Session not found or arXiv paper not found"}
    }
)
async def add_arxiv(
    background_tasks: BackgroundTasks,
    sid: int = Query(..., description="Session ID"),
    payload: dict = None,
    db: DBSession = Depends(get_db)
):
    """Download and process an arXiv paper in the background"""
    logger.info(f"Adding arXiv paper to session {sid}")
    sess = db.get(SessionModel, sid)
    if not sess:
        raise HTTPException(404, "Session not found")
    arxiv_id = payload.get("arxiv_id")
    if not arxiv_id:
        raise HTTPException(400, "arxiv_id is required")

    uploads = _uploads_dir(sid)
    uploads.mkdir(parents=True, exist_ok=True)
    doc = Document(session_id=sid, source_type=DocSource.arxiv, status=DocStatus.downloading, arxiv_id=arxiv_id)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    logger.info(f"Created document record {doc.id} for arXiv paper {arxiv_id}, scheduling background processing")
    
    # Schedule background processing
    background_tasks.add_task(
        process_arxiv_document,
        doc_id=doc.id,
        session_id=sid,
        arxiv_id=arxiv_id,
        uploads_dir=uploads,
        graph_dir=_graph_dir(sid),
        lock_file=_lock_file(sid)
    )
    
    return {"id": doc.id, "status": doc.status.value, "arxiv_id": arxiv_id}
