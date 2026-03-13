"""Unit tests for progress tracking log handler."""

import logging


def _record(msg: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="nano-graphrag",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )


def test_progress_handler_updates_document_fields(test_db):
    from app.models import Document, DocSource, DocStatus
    from app.services.progress_tracker import DocumentProgressHandler

    doc = Document(session_id=1, source_type=DocSource.upload, status=DocStatus.inserting, title="t")
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)

    handler = DocumentProgressHandler(doc.id, test_db)

    handler.emit(_record("[New Docs] inserting 1 docs"))
    test_db.refresh(doc)
    assert doc.processing_phase == "text_chunking"
    assert doc.progress_percent == 20

    handler.emit(_record("[New Chunks] inserting 2 chunks"))
    test_db.refresh(doc)
    assert doc.processing_phase == "entity_extraction"
    assert doc.progress_percent == 30

    handler.emit(_record("Ensuring graph connectivity"))
    test_db.refresh(doc)
    assert doc.processing_phase == "graph_clustering"
    assert doc.progress_percent == 60


def test_progress_handler_rollback_on_db_error(monkeypatch, test_db):
    from app.models import Document, DocSource, DocStatus
    from app.services.progress_tracker import DocumentProgressHandler

    doc = Document(session_id=1, source_type=DocSource.upload, status=DocStatus.inserting, title="t")
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)

    handler = DocumentProgressHandler(doc.id, test_db)

    # Force commit to fail to exercise exception handling + rollback path
    def boom():
        raise RuntimeError("commit failed")

    monkeypatch.setattr(test_db, "commit", boom)

    # Should not raise
    handler.emit(_record("[New Docs] inserting 1 docs"))
