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
import time
from datetime import datetime, timezone

from ..models import Document, DocStatus, Message, Role, ProcessingPhase
from ..utils.pdf_utils import extract_text
from ..utils.arxiv_utils import download_pdf
from ..utils.locks import session_lock
from ..services.graphrag_service import DashRAGService
from ..services.progress_tracker import attach_progress_handler, detach_progress_handler
from ..services.eta_estimator import estimate_remaining_ms
from ..services.query_progress import (
    start_message_progress,
    update_message_progress,
    complete_message_progress,
    fail_message_progress,
)
from ..db import SessionLocal
from ..config import settings

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
    qp_kwargs: dict,
    estimated_total_ms: int = 12000,
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
        op_started = time.perf_counter()
        op_started_dt = datetime.now(timezone.utc)
        mode = str((qp_kwargs or {}).get("mode") or "local")
        start_message_progress(
            message_id=message_id,
            session_id=session_id,
            estimated_total_ms=estimated_total_ms,
            mode=mode,
        )

        def _sync_progress(stage: str, stage_label: str, progress_percent: int):
            elapsed_ms = int((time.perf_counter() - op_started) * 1000)
            refined_total_ms, remaining_ms = estimate_remaining_ms(
                elapsed_ms=elapsed_ms,
                progress_percent=progress_percent,
                initial_total_ms=estimated_total_ms,
            )
            update_message_progress(
                message_id,
                stage=stage,
                stage_label=stage_label,
                progress_percent=progress_percent,
                elapsed_ms=elapsed_ms,
                estimated_total_ms=refined_total_ms,
                estimated_remaining_ms=remaining_ms,
            )

        _sync_progress("preparing_query", "Preparing query", 10)
        
        # Execute query against knowledge graph
        rag = DashRAGService(graph_dir)
        try:
            # Run async GraphRAG operation with a hard timeout to prevent infinite hangs.
            # Timeout is controlled by QUERY_TIMEOUT_SECONDS env var (default: 180s).
            _sync_progress("querying_graphrag", "Querying knowledge graph", 45)
            cleaned_qp_kwargs = {k: v for k, v in (qp_kwargs or {}).items() if v is not None}
            async def _timed_query():
                return await asyncio.wait_for(
                    rag.query(prompt, **cleaned_qp_kwargs),
                    timeout=float(settings.query_timeout_seconds)
                )
            answer_payload = asyncio.run(_timed_query())
            _sync_progress("building_response", "Building response", 85)
            logger.info(f"Query completed successfully for message {message_id}")
        except asyncio.TimeoutError:
            timeout_secs = settings.query_timeout_seconds
            error_msg = f"Query timed out after {timeout_secs}s. Try a shorter query or switch to naive mode."
            logger.error(f"Message {message_id} query timed out after {timeout_secs}s")
            elapsed_ms = int((time.perf_counter() - op_started) * 1000)
            fail_message_progress(message_id, elapsed_ms=elapsed_ms, error=error_msg)
            m_asst = Message(
                session_id=session_id,
                role=Role.assistant,
                content={
                    "text": error_msg,
                    "error": True,
                    "timing": {
                        "started_at": op_started_dt.isoformat(),
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                        "duration_ms": elapsed_ms,
                    },
                },
            )
            db.add(m_asst)
            db.commit()
            return
        except Exception as e:
            error_msg = f"GraphRAG query failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            elapsed_ms = int((time.perf_counter() - op_started) * 1000)
            fail_message_progress(message_id, elapsed_ms=elapsed_ms, error=str(e))
            # Create error response message
            m_asst = Message(
                session_id=session_id,
                role=Role.assistant,
                content={
                    "text": f"Error: {str(e)}",
                    "error": True,
                    "timing": {
                        "started_at": op_started_dt.isoformat(),
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                        "duration_ms": elapsed_ms,
                    },
                },
            )
            db.add(m_asst)
            db.commit()
            return
        
        # Create assistant response message
        elapsed_ms = int((time.perf_counter() - op_started) * 1000)
        completed_at = datetime.now(timezone.utc).isoformat()
        started_at = op_started_dt.isoformat()

        response_content = answer_payload if isinstance(answer_payload, dict) else {"text": str(answer_payload)}
        response_content["timing"] = {
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_ms": elapsed_ms,
            "mode": mode,
            "estimated_total_ms": max(int(estimated_total_ms), 1),
        }

        m_asst = Message(
            session_id=session_id,
            role=Role.assistant,
            content=response_content,
        )
        db.add(m_asst)
        db.commit()
        complete_message_progress(message_id, completed_in_ms=elapsed_ms)
        logger.info(f"Created assistant response message for query {message_id}")
    
    except Exception as e:
        logger.error(f"Unexpected error processing message {message_id}: {str(e)}", exc_info=True)
    finally:
        db.close()
