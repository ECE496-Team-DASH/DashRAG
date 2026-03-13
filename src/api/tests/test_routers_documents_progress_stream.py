"""Tests for /documents/progress-stream SSE endpoint."""

import json
from unittest.mock import patch


def test_progress_stream_404_for_missing_doc(client, auth_headers, test_session):
    resp = client.get(
        f"/documents/progress-stream?sid={test_session.id}&doc_id=9999",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@patch("app.routers.documents.asyncio.sleep", autospec=True)
def test_progress_stream_emits_events_and_completes(mock_sleep, client, auth_headers, test_session, test_db):
    from app.models import Document, DocSource, DocStatus

    # Speed up loop
    async def fast_sleep(_):
        return None

    mock_sleep.side_effect = fast_sleep

    doc = Document(session_id=test_session.id, source_type=DocSource.upload, status=DocStatus.inserting, title="t")
    test_db.add(doc)
    test_db.commit()
    test_db.refresh(doc)

    # Patch SessionLocal used inside the generator to return our test_db, and
    # mutate the document to ready after first fetch.
    from app.routers import documents as docs_router

    calls = {"n": 0}

    class _DBWrapper:
        def __init__(self):
            self._db = test_db
        def get(self, model, pk):
            calls["n"] += 1
            obj = self._db.get(model, pk)
            if calls["n"] == 1 and obj:
                obj.progress_percent = 50
                obj.processing_phase = "entity_extraction"
                self._db.commit()
            elif calls["n"] == 2 and obj:
                obj.status = DocStatus.ready
                obj.progress_percent = 100
                obj.processing_phase = None
                self._db.commit()
            return obj
        def close(self):
            return None

    with patch.object(docs_router, "SessionLocal", autospec=True) as mock_sl:
        mock_sl.return_value = _DBWrapper()

        with client.stream(
            "GET",
            f"/documents/progress-stream?sid={test_session.id}&doc_id={doc.id}",
            headers=auth_headers,
        ) as resp:
            assert resp.status_code == 200
            body = "".join([chunk.decode("utf-8") for chunk in resp.iter_raw()])

    # Parse the SSE data lines
    data_lines = [ln for ln in body.splitlines() if ln.startswith("data: ")]
    assert len(data_lines) >= 2

    first = json.loads(data_lines[0][6:])
    assert first["document_id"] == doc.id

    # Should include terminal complete event
    assert any("complete" in ln for ln in data_lines)
