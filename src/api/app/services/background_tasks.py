"""
Background task processing for document uploads, arXiv papers, and message queries.

This module handles asynchronous processing to avoid blocking
API responses during PDF extraction, knowledge graph insertion, and query execution.
"""

from pathlib import Path
from sqlalchemy.orm import Session as DBSession
import logging
import traceback
import asyncio

from ..models import Document, DocStatus, Message, Role, ProcessingPhase
from ..utils.pdf_utils import extract_text
from ..utils.arxiv_utils import download_pdf
from ..utils.locks import session_lock
from ..services.graphrag_service import DashRAGService
from ..services.progress_tracker import attach_progress_handler, detach_progress_handler
from ..db import SessionLocal

logger = logging.getLogger(__name__)


def process_uploaded_document(
    doc_id: int,
    session_id: int,
    pdf_path: Path,
    graph_dir: Path,
    lock_file: Path
):
    """
    Background task to process an uploaded PDF document.
    
    This runs synchronously in FastAPI's background thread pool.
    GraphRAG async operations are executed via asyncio.run().
    
    Args:
        doc_id: Document ID
        session_id: Session ID
        pdf_path: Path to uploaded PDF file
        graph_dir: Path to session's knowledge graph directory
        lock_file: Path to session lock file
    """
    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if not doc:
            logger.error(f"Document {doc_id} not found for processing")
            return
        
        logger.info(f"Background processing document {doc_id} from session {session_id}")
        
        # Phase 1: Extract text from PDF
        doc.processing_phase = ProcessingPhase.pdf_extraction.value
        doc.progress_percent = 10
        db.commit()
        
        try:
            text, pages = extract_text(pdf_path)
            doc.pages = pages
            doc.progress_percent = 15
            db.commit()
            logger.info(f"Extracted {pages} pages from document {doc_id}")
        except Exception as e:
            error_msg = f"Failed to extract text from PDF: {str(e)}"
            logger.error(error_msg, exc_info=True)
            doc.status = DocStatus.error
            doc.insert_log = f"{error_msg}\n\nTraceback:\n{traceback.format_exc()}"
            db.commit()
            return
        
        # Phase 2: Insert into knowledge graph with progress tracking
        graph_dir.mkdir(parents=True, exist_ok=True)
        
        # Attach progress handler to track nano-graphrag logs
        progress_handler = attach_progress_handler(doc_id, db)
        
        try:
            with session_lock(lock_file):
                try:
                    # Run async GraphRAG operation in new event loop
                    asyncio.run(DashRAGService(graph_dir).insert_texts(text))
                    doc.status = DocStatus.ready
                    doc.processing_phase = None
                    doc.progress_percent = 100
                    
                    # Check if there were any warnings in the log
                    if "incomplete knowledge graph" in (doc.insert_log or "").lower():
                        doc.insert_log = (doc.insert_log or "") + "\n\nWarning: Community reports may be incomplete due to LLM JSON formatting issues."
                    
                    logger.info(f"Document {doc_id} successfully inserted into knowledge graph")
                except Exception as e:
                    error_msg = f"GraphRAG insertion failed: {str(e)}"
                    
                    # Check if it's a JSON parsing error that we can recover from
                    if "JSONDecodeError" in str(e) or "Expecting ':' delimiter" in str(e):
                        logger.warning(f"Document {doc_id} encountered JSON parsing errors during community report generation, but entities may have been extracted")
                        # Mark as ready with a warning note
                        doc.status = DocStatus.ready
                        doc.processing_phase = None
                        doc.progress_percent = 100
                        doc.insert_log = f"Warning: Community reports incomplete due to LLM response formatting issues.\n\nEntities and relationships were successfully extracted, but some high-level summaries may be missing.\n\nOriginal error: {str(e)}"
                        logger.info(f"Document {doc_id} marked as ready with warnings")
                    else:
                        logger.error(error_msg, exc_info=True)
                        doc.status = DocStatus.error
                        doc.processing_phase = None
                        doc.progress_percent = 0
                        doc.insert_log = f"{error_msg}\n\nTraceback:\n{traceback.format_exc()}"
                db.commit()
        finally:
            # Always remove the progress handler
            detach_progress_handler(progress_handler)
    
    except Exception as e:
        logger.error(f"Unexpected error processing document {doc_id}: {str(e)}", exc_info=True)
        try:
            doc = db.get(Document, doc_id)
            if doc:
                doc.status = DocStatus.error
                doc.insert_log = f"Unexpected error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def process_arxiv_document(
    doc_id: int,
    session_id: int,
    arxiv_id: str,
    uploads_dir: Path,
    graph_dir: Path,
    lock_file: Path
):
    """
    Background task to download and process an arXiv paper.
    
    This runs synchronously in FastAPI's background thread pool.
    GraphRAG async operations are executed via asyncio.run().
    
    Args:
        doc_id: Document ID
        session_id: Session ID
        arxiv_id: arXiv paper ID (e.g., "1706.03762")
        uploads_dir: Path to session's uploads directory
        graph_dir: Path to session's knowledge graph directory
        lock_file: Path to session lock file
    """
    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if not doc:
            logger.error(f"Document {doc_id} not found for processing")
            return
        
        logger.info(f"Background processing arXiv paper {arxiv_id} (doc {doc_id}) from session {session_id}")
        
        # Download PDF from arXiv
        try:
            pdf_path = Path(download_pdf(arxiv_id, uploads_dir))
            doc.local_pdf_path = str(pdf_path)
            doc.status = DocStatus.inserting
            db.commit()
            logger.info(f"Downloaded arXiv PDF {arxiv_id} to {pdf_path}")
        except Exception as e:
            error_msg = f"Failed to download arXiv paper {arxiv_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            doc.status = DocStatus.error
            doc.insert_log = f"{error_msg}\n\nTraceback:\n{traceback.format_exc()}"
            db.commit()
            return
        
        # Extract text from PDF
        try:
            text, pages = extract_text(pdf_path)
            doc.pages = pages
            db.commit()
            logger.info(f"Extracted {pages} pages from arXiv paper {arxiv_id}")
        except Exception as e:
            error_msg = f"Failed to extract text from PDF: {str(e)}"
            logger.error(error_msg, exc_info=True)
            doc.status = DocStatus.error
            doc.insert_log = f"{error_msg}\n\nTraceback:\n{traceback.format_exc()}"
            db.commit()
            return
        
        # Phase 2: Insert into knowledge graph with progress tracking
        graph_dir.mkdir(parents=True, exist_ok=True)
        
        # Attach progress handler to track nano-graphrag logs
        progress_handler = attach_progress_handler(doc_id, db)
        
        try:
            with session_lock(lock_file):
                try:
                    # Run async GraphRAG operation in new event loop
                    asyncio.run(DashRAGService(graph_dir).insert_texts(text))
                    doc.status = DocStatus.ready
                    doc.processing_phase = None
                    doc.progress_percent = 100
                    
                    # Check if there were any warnings in the log
                    if "incomplete knowledge graph" in (doc.insert_log or "").lower():
                        doc.insert_log = (doc.insert_log or "") + "\n\nWarning: Community reports may be incomplete due to LLM JSON formatting issues."
                    
                    logger.info(f"Document {doc_id} (arXiv: {arxiv_id}) successfully inserted into knowledge graph")
                except Exception as e:
                    error_msg = f"GraphRAG insertion failed: {str(e)}"
                    
                    # Check if it's a JSON parsing error that we can recover from
                    if "JSONDecodeError" in str(e) or "Expecting ':' delimiter" in str(e):
                        logger.warning(f"Document {doc_id} (arXiv: {arxiv_id}) encountered JSON parsing errors during community report generation, but entities may have been extracted")
                        # Mark as ready with a warning note
                        doc.status = DocStatus.ready
                        doc.processing_phase = None
                        doc.progress_percent = 100
                        doc.insert_log = f"Warning: Community reports incomplete due to LLM response formatting issues.\n\nEntities and relationships were successfully extracted, but some high-level summaries may be missing.\n\nOriginal error: {str(e)}"
                        logger.info(f"Document {doc_id} (arXiv: {arxiv_id}) marked as ready with warnings")
                    else:
                        logger.error(error_msg, exc_info=True)
                        doc.status = DocStatus.error
                        doc.processing_phase = None
                        doc.progress_percent = 0
                        doc.insert_log = f"{error_msg}\n\nTraceback:\n{traceback.format_exc()}"
                db.commit()
        finally:
            # Always remove the progress handler
            detach_progress_handler(progress_handler)
    
    except Exception as e:
        logger.error(f"Unexpected error processing arXiv document {doc_id}: {str(e)}", exc_info=True)
        try:
            doc = db.get(Document, doc_id)
            if doc:
                doc.status = DocStatus.error
                doc.insert_log = f"Unexpected error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def process_message_query(
    message_id: int,
    session_id: int,
    prompt: str,
    graph_dir: Path,
    qp_kwargs: dict
):
    """
    Background task to process a user message query.
    
    This runs synchronously in FastAPI's background thread pool.
    GraphRAG async operations are executed via asyncio.run().
    
    Args:
        message_id: User message ID
        session_id: Session ID
        prompt: User's query text
        graph_dir: Path to session's knowledge graph directory
        qp_kwargs: Query parameters for GraphRAG
    """
    db = SessionLocal()
    try:
        msg = db.get(Message, message_id)
        if not msg:
            logger.error(f"Message {message_id} not found for processing")
            return
        
        logger.info(f"Background processing query message {message_id} from session {session_id}")
        
        # Execute query against knowledge graph
        rag = DashRAGService(graph_dir)
        try:
            # Run async GraphRAG operation in new event loop
            answer = asyncio.run(rag.query(prompt, **{k:v for k,v in qp_kwargs.items() if v is not None}))
            logger.info(f"Query completed successfully for message {message_id}")
        except Exception as e:
            error_msg = f"GraphRAG query failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # Create error response message
            m_asst = Message(
                session_id=session_id,
                role=Role.assistant,
                content={"text": f"Error: {str(e)}", "error": True}
            )
            db.add(m_asst)
            db.commit()
            return
        
        # Create assistant response message
        m_asst = Message(
            session_id=session_id,
            role=Role.assistant,
            content={"text": answer}
        )
        db.add(m_asst)
        db.commit()
        logger.info(f"Created assistant response message for query {message_id}")
    
    except Exception as e:
        logger.error(f"Unexpected error processing message {message_id}: {str(e)}", exc_info=True)
    finally:
        db.close()
