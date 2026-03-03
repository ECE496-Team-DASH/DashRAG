"""
Logging utilities for DashRAG API.

Provides loggers for:
- Knowledge Graph statistics (insertions, queries, graph size)
- Runtime and memory stats
"""

import logging
import time
import os
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Configure dedicated loggers
kg_logger = logging.getLogger("dashrag.knowledge_graph")
perf_logger = logging.getLogger("dashrag.performance")


class MemoryTracker:
    """Track memory usage during operations."""
    
    def __init__(self):
        self._process = None
    
    @property
    def process(self):
        if self._process is None and PSUTIL_AVAILABLE:
            self._process = psutil.Process(os.getpid())
        return self._process
    
    def get_memory_mb(self) -> float:
        """Get current memory usage in MB."""
        if not PSUTIL_AVAILABLE or self.process is None:
            return 0.0
        return self.process.memory_info().rss / (1024 * 1024)


memory_tracker = MemoryTracker()


@contextmanager
def timed_operation(operation_name: str, log_memory: bool = False):
    """
    Context manager for timing operations with optional memory tracking.
    
    Usage:
        with timed_operation("insert_document", log_memory=True):
            # ... operation code ...
    """
    start_time = time.perf_counter()
    start_memory = memory_tracker.get_memory_mb() if log_memory else None
    
    perf_logger.debug(f"[START] {operation_name}")
    
    try:
        yield
    finally:
        duration = time.perf_counter() - start_time
        
        log_msg = f"[END] {operation_name} - Duration: {duration:.3f}s"
        
        if log_memory and start_memory is not None:
            end_memory = memory_tracker.get_memory_mb()
            memory_delta = end_memory - start_memory
            log_msg += f" | Memory: {end_memory:.1f}MB (Δ{memory_delta:+.1f}MB)"
        
        perf_logger.info(log_msg)


class KnowledgeGraphLogger:
    """Logger for Knowledge Graph operations and statistics."""
    
    @staticmethod
    def log_graph_stats(graph_dir: Path, session_id: int):
        """Log statistics about a knowledge graph directory."""
        if not graph_dir.exists():
            kg_logger.warning(f"[Session {session_id}] Graph directory does not exist: {graph_dir}")
            return
        
        total_size_mb = 0
        file_count = 0
        
        for file_path in graph_dir.rglob("*"):
            if file_path.is_file():
                total_size_mb += file_path.stat().st_size / (1024 * 1024)
                file_count += 1
        
        kg_logger.info(
            f"[Session {session_id}] Graph Stats: {file_count} files, {total_size_mb:.2f}MB total"
        )
    
    @staticmethod
    def log_insertion_start(session_id: int, doc_id: int, text_length: int):
        """Log the start of a document insertion."""
        kg_logger.info(
            f"[Session {session_id}] Starting insertion of doc {doc_id} ({text_length:,} characters)"
        )
    
    @staticmethod
    def log_insertion_complete(session_id: int, doc_id: int, duration: float):
        """Log completion of a document insertion."""
        kg_logger.info(
            f"[Session {session_id}] Completed insertion of doc {doc_id} in {duration:.2f}s"
        )
    
    @staticmethod
    def log_query_start(session_id: int, mode: str, prompt_length: int):
        """Log the start of a query."""
        kg_logger.info(
            f"[Session {session_id}] Query started - Mode: {mode}, Prompt: {prompt_length} chars"
        )
    
    @staticmethod
    def log_query_complete(session_id: int, mode: str, duration: float, response_length: int):
        """Log completion of a query."""
        kg_logger.info(
            f"[Session {session_id}] Query completed - Mode: {mode}, Duration: {duration:.2f}s, Response: {response_length} chars"
        )


# Convenience instance
kg_log = KnowledgeGraphLogger()
