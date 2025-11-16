"""
Progress tracking for document processing via log parsing.

This module provides a custom logging handler that parses nano-graphrag
log messages and updates document processing progress in real-time.
"""

import logging
import re
from sqlalchemy.orm import Session as DBSession
from ..models import Document, ProcessingPhase
from ..db import SessionLocal

logger = logging.getLogger(__name__)


class DocumentProgressHandler(logging.Handler):
    """
    Custom log handler that parses nano-graphrag logs and updates
    document progress in the database.
    """
    
    def __init__(self, doc_id: int, db: DBSession):
        super().__init__()
        self.doc_id = doc_id
        self.db = db
        self.setLevel(logging.INFO)
        
    def emit(self, record: logging.LogRecord):
        """
        Parse log messages and update document progress.
        """
        try:
            msg = record.getMessage()
            
            # Parse different log patterns from nano-graphrag
            updates = {}
            
            if "[New Docs]" in msg:
                # Document chunking starting
                match = re.search(r'inserting (\d+) docs', msg)
                if match:
                    updates['processing_phase'] = ProcessingPhase.text_chunking.value
                    updates['progress_percent'] = 20
                    logger.debug(f"Doc {self.doc_id}: Text chunking phase")
            
            elif "[New Chunks]" in msg:
                # Chunks created, entity extraction starting
                match = re.search(r'inserting (\d+) chunks', msg)
                if match:
                    updates['processing_phase'] = ProcessingPhase.entity_extraction.value
                    updates['progress_percent'] = 30
                    logger.debug(f"Doc {self.doc_id}: Entity extraction phase")
            
            elif "[Entity Extraction]" in msg:
                # Entity extraction in progress
                updates['processing_phase'] = ProcessingPhase.entity_extraction.value
                updates['progress_percent'] = 40
                logger.debug(f"Doc {self.doc_id}: Extracting entities")
            
            elif "Processing" in msg and "documents with GenKG" in msg:
                # GenKG processing started
                updates['progress_percent'] = 50
                logger.debug(f"Doc {self.doc_id}: GenKG processing")
            
            elif "Ensuring graph connectivity" in msg:
                # Graph clustering phase
                updates['processing_phase'] = ProcessingPhase.graph_clustering.value
                updates['progress_percent'] = 60
                logger.debug(f"Doc {self.doc_id}: Graph clustering")
            
            elif "About to merge" in msg and "node types" in msg:
                # Merging entities
                updates['progress_percent'] = 70
                logger.debug(f"Doc {self.doc_id}: Merging entities")
            
            elif "GenKG successfully extracted" in msg:
                # Entities extracted, moving to community reports
                match = re.search(r'extracted (\d+) entities', msg)
                if match:
                    updates['processing_phase'] = ProcessingPhase.community_reports.value
                    updates['progress_percent'] = 75
                    logger.debug(f"Doc {self.doc_id}: Community reports phase")
            
            elif "[Community Report]" in msg:
                # Community report generation started
                updates['processing_phase'] = ProcessingPhase.community_reports.value
                updates['progress_percent'] = 80
                logger.debug(f"Doc {self.doc_id}: Generating community reports")
            
            elif "Processing" in msg and "connected components for clustering" in msg:
                # Clustering in progress
                updates['progress_percent'] = 85
                logger.debug(f"Doc {self.doc_id}: Clustering components")
            
            elif "Generating by levels" in msg:
                # Final community generation
                updates['progress_percent'] = 90
                logger.debug(f"Doc {self.doc_id}: Finalizing communities")
            
            elif "Writing graph with" in msg:
                # Writing final graph
                updates['processing_phase'] = ProcessingPhase.finalizing.value
                updates['progress_percent'] = 95
                logger.debug(f"Doc {self.doc_id}: Writing graph")
            
            # Only update if we have changes
            if updates:
                doc = self.db.get(Document, self.doc_id)
                if doc:
                    for key, value in updates.items():
                        setattr(doc, key, value)
                    self.db.commit()
            
        except Exception as e:
            logger.error(f"Error in progress handler for doc {self.doc_id}: {e}", exc_info=True)
            # Don't raise - we don't want to break the main processing
            try:
                self.db.rollback()
            except:
                pass


def attach_progress_handler(doc_id: int, db: DBSession) -> DocumentProgressHandler:
    """
    Attach a progress handler to the nano-graphrag logger.
    
    Args:
        doc_id: Document ID to track
        db: Database session
        
    Returns:
        The created handler (so it can be removed later)
    """
    handler = DocumentProgressHandler(doc_id, db)
    nano_logger = logging.getLogger("nano-graphrag")
    nano_logger.addHandler(handler)
    return handler


def detach_progress_handler(handler: DocumentProgressHandler):
    """
    Remove a progress handler from the nano-graphrag logger.
    
    Args:
        handler: The handler to remove
    """
    try:
        nano_logger = logging.getLogger("nano-graphrag")
        nano_logger.removeHandler(handler)
    except Exception as e:
        logger.error(f"Error removing progress handler: {e}")
