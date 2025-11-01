
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from sqlalchemy.orm import Session as DBSession
from pathlib import Path
import logging
import traceback

from ..db import SessionLocal
from ..models import Session as SessionModel, Document, DocSource, DocStatus
from ..utils.pdf_utils import extract_text
from ..utils.arxiv_utils import search_arxiv, download_pdf
from ..services.graphrag_service import DashRAGService
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

def _session_root(sid: str) -> Path:
    return settings.data_root / "sessions" / sid
def _uploads_dir(sid: str) -> Path:
    return _session_root(sid) / "uploads"
def _lock_file(sid: str) -> Path:
    return _session_root(sid) / ".lock"
def _graph_dir(sid: str) -> Path:
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
                            "id": "doc_abc123def456",
                            "title": "transformer_paper.pdf",
                            "source_type": "upload",
                            "status": "ready",
                            "arxiv_id": None,
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
                }
            }
        }
    }
)
def list_docs(sid: str = Query(..., description="Session ID"), db: DBSession = Depends(get_db)):
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
    status_code=200,
    summary="Upload PDF document",
    description="""
    Upload a PDF file and add it to the session's knowledge graph.
    
    **Process:**
    1. File is saved to session's uploads directory
    2. Text is extracted from PDF
    3. Entities and relationships are extracted
    4. Knowledge graph is updated
    5. Status changes: `inserting` → `ready` (or `error`)
    
    **Request:** Multipart form-data with `file` field
    
    **Accepts:** PDF files only (`.pdf` extension)
    
    **Query parameters:**
    - `sid`: Session ID
    
    **Note:** This is a synchronous operation that may take several seconds for large PDFs.
    """,
    responses={
        200: {
            "description": "Document uploaded and processed",
            "content": {
                "application/json": {
                    "example": {
                        "id": "doc_abc123def456",
                        "status": "ready",
                        "title": "my_research_paper.pdf"
                    }
                }
            }
        },
        400: {"description": "Invalid file format (must be PDF)"},
        404: {"description": "Session not found"}
    }
)
async def upload_pdf(sid: str = Query(..., description="Session ID"), file: UploadFile = File(...), db: DBSession = Depends(get_db)):
    """Upload a PDF and add it to the knowledge graph"""
    logger.info(f"Uploading PDF '{file.filename}' to session {sid}")
    sess = db.get(SessionModel, sid)
    if not sess:
        raise HTTPException(404, "Session not found")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    uploads = _uploads_dir(sid); uploads.mkdir(parents=True, exist_ok=True)
    doc = Document(session_id=sid, source_type=DocSource.upload, status=DocStatus.inserting, title=file.filename)
    db.add(doc); db.commit(); db.refresh(doc)

    try:
        pdf_path = uploads / f"{doc.id}.pdf"
        data = await file.read()
        pdf_path.write_bytes(data)
        doc.local_pdf_path = str(pdf_path)
        db.commit()
        logger.info(f"PDF saved to {pdf_path}")

        text, pages = extract_text(pdf_path)
        doc.pages = pages; db.commit()
        logger.info(f"Extracted {pages} pages from PDF")

        graph_dir = _graph_dir(sid); graph_dir.mkdir(parents=True, exist_ok=True)
        with session_lock(_lock_file(sid)):
            try:
                DashRAGService(graph_dir).insert_texts(text)
                doc.status = DocStatus.ready
                logger.info(f"Document {doc.id} successfully inserted into knowledge graph")
            except Exception as e:
                error_msg = f"GraphRAG insertion failed: {str(e)}"
                logger.error(error_msg, exc_info=True)
                doc.status = DocStatus.error
                doc.insert_log = f"{error_msg}\n\nTraceback:\n{traceback.format_exc()}"
            db.commit()
    except Exception as e:
        error_msg = f"Failed to process PDF: {str(e)}"
        logger.error(error_msg, exc_info=True)
        doc.status = DocStatus.error
        doc.insert_log = f"{error_msg}\n\nTraceback:\n{traceback.format_exc()}"
        db.commit()

    return {"id": doc.id, "status": doc.status.value, "title": doc.title}

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
def preview_arxiv(sid: str = Query(..., description="Session ID"), query: str = Query(..., description="Search query"), max_results: int = Query(5, description="Maximum number of results"), db: DBSession = Depends(get_db)):
    """Preview arXiv search results without adding documents"""
    if not db.get(SessionModel, sid):
        raise HTTPException(404, "Session not found")
    max_results = min(max_results, settings.arxiv_max_results)
    return search_arxiv(query, max_results=max_results)

@router.post(
    "/add-arxiv", 
    response_model=dict,
    status_code=200,
    summary="Add arXiv paper to session",
    description="""
    Download an arXiv paper and add it to the session's knowledge graph.
    
    **Process:**
    1. Download PDF from arXiv
    2. Extract text
    3. Build knowledge graph
    4. Status transitions: `downloading` → `inserting` → `ready` (or `error`)
    
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
    
    **Note:** This is synchronous and may take 10-30 seconds depending on paper size.
    """,
    responses={
        200: {
            "description": "Paper added successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "doc_xyz789uvw012",
                        "status": "ready",
                        "arxiv_id": "1706.03762"
                    }
                }
            }
        },
        400: {"description": "Missing or invalid arxiv_id"},
        404: {"description": "Session not found or arXiv paper not found"}
    }
)
def add_arxiv(sid: str = Query(..., description="Session ID"), payload: dict = None, db: DBSession = Depends(get_db)):
    """Download and add an arXiv paper to the knowledge graph"""
    logger.info(f"Adding arXiv paper to session {sid}")
    sess = db.get(SessionModel, sid)
    if not sess:
        raise HTTPException(404, "Session not found")
    arxiv_id = payload.get("arxiv_id")
    if not arxiv_id:
        raise HTTPException(400, "arxiv_id is required")

    uploads = _uploads_dir(sid); uploads.mkdir(parents=True, exist_ok=True)
    doc = Document(session_id=sid, source_type=DocSource.arxiv, status=DocStatus.downloading, arxiv_id=arxiv_id)
    db.add(doc); db.commit(); db.refresh(doc)
    logger.info(f"Created document record {doc.id} for arXiv paper {arxiv_id}")

    try:
        pdf_path = Path(download_pdf(arxiv_id, uploads))
        doc.local_pdf_path = str(pdf_path); doc.status = DocStatus.inserting
        db.commit()
        logger.info(f"Downloaded arXiv PDF to {pdf_path}")

        text, pages = extract_text(pdf_path)
        doc.pages = pages; db.commit()
        logger.info(f"Extracted {pages} pages from arXiv PDF")

        graph_dir = _graph_dir(sid); graph_dir.mkdir(parents=True, exist_ok=True)
        with session_lock(_lock_file(sid)):
            try:
                DashRAGService(graph_dir).insert_texts(text)
                doc.status = DocStatus.ready
                logger.info(f"Document {doc.id} (arXiv: {arxiv_id}) successfully inserted into knowledge graph")
            except Exception as e:
                error_msg = f"GraphRAG insertion failed: {str(e)}"
                logger.error(error_msg, exc_info=True)
                doc.status = DocStatus.error
                doc.insert_log = f"{error_msg}\n\nTraceback:\n{traceback.format_exc()}"
            db.commit()
    except Exception as e:
        error_msg = f"Failed to process arXiv paper {arxiv_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        doc.status = DocStatus.error
        doc.insert_log = f"{error_msg}\n\nTraceback:\n{traceback.format_exc()}"
        db.commit()

    return {"id": doc.id, "status": doc.status.value, "arxiv_id": arxiv_id}
