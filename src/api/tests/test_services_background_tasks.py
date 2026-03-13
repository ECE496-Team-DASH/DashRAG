"""Unit tests for background task processors."""

from pathlib import Path
from unittest.mock import patch


def test_process_message_query_creates_assistant_error_on_exception(test_db, tmp_path):
    from app.models import Message, Role, Session
    from app.services import background_tasks

    # create minimal session + user message
    sess = Session(user_id=1, title="t", graph_dir=str(tmp_path / "g"))
    test_db.add(sess)
    test_db.commit()

    m = Message(session_id=sess.id, role=Role.user, content={"text": "q"})
    test_db.add(m)
    test_db.commit()
    test_db.refresh(m)

    # background_tasks creates its own DB session via SessionLocal; emulate that with a new session
    engine = test_db.get_bind()
    SessionMaker = type(test_db)

    def _new_session():
        return SessionMaker(bind=engine)

    with patch.object(background_tasks, "SessionLocal", side_effect=_new_session):
        with patch.object(background_tasks, "DashRAGService") as mock_rag:
            mock_rag.return_value.query.side_effect = RuntimeError("boom")
            background_tasks.process_message_query(
                message_id=m.id,
                session_id=sess.id,
                prompt="q",
                graph_dir=Path(sess.graph_dir),
                qp_kwargs={},
            )

    # Query using the original test_db session
    rows = test_db.query(Message).filter(Message.session_id == sess.id).order_by(Message.id.asc()).all()
    assert len(rows) == 2
    assert rows[1].role == Role.assistant
    assert rows[1].content.get("error") is True


def test_process_uploaded_document_sets_error_when_pdf_extract_fails(test_db, tmp_path):
    from app.models import Document, DocSource, DocStatus
    from app.services import background_tasks

    doc = Document(session_id=1, source_type=DocSource.upload, status=DocStatus.inserting, title="t")
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)

    pdf_path = tmp_path / "x.pdf"
    pdf_path.write_bytes(b"not really pdf")

    engine = test_db.get_bind()
    SessionMaker = type(test_db)

    def _new_session():
        return SessionMaker(bind=engine)

    with patch.object(background_tasks, "SessionLocal", side_effect=_new_session):
        with patch.object(background_tasks, "extract_text", side_effect=RuntimeError("bad pdf")):
            background_tasks.process_uploaded_document(
                doc_id=doc.id,
                session_id=1,
                pdf_path=pdf_path,
                graph_dir=tmp_path / "graph",
                lock_file=tmp_path / ".lock",
            )

    # Reload doc state
    test_db.expire_all()
    doc2 = test_db.get(Document, doc.id)
    assert doc2.status == DocStatus.error
    assert "Failed to extract text" in (doc2.insert_log or "")
