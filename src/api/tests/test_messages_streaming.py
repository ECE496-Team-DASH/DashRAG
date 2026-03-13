"""Tests for /messages/stream endpoint error branches."""

import json
from unittest.mock import patch


def _add_ready_doc(test_db, sid: int):
    from app.models import Document, DocSource, DocStatus

    d = Document(session_id=sid, source_type=DocSource.upload, status=DocStatus.ready, title="t")
    test_db.add(d)
    test_db.commit()


def test_stream_returns_value_error_as_sse_error(client, auth_headers, test_session, test_db):
    _add_ready_doc(test_db, test_session.id)

    with patch("app.routers.messages.DashRAGService") as mock_rag:
        async def boom(*args, **kwargs):
            raise ValueError("bad params")
        mock_rag.return_value.query.side_effect = boom

        with client.stream(
            "POST",
            f"/messages/stream?sid={test_session.id}",
            headers=auth_headers,
            json={"content": "hi"},
        ) as resp:
            assert resp.status_code == 200
            body = "".join([c.decode("utf-8") for c in resp.iter_raw()])

    assert "data: " in body
    payload = json.loads([ln for ln in body.splitlines() if ln.startswith("data: ")][0][6:])
    assert payload["type"] == "error"
    assert "bad params" in payload["message"]


def test_stream_returns_generic_exception_as_sse_error(client, auth_headers, test_session, test_db):
    _add_ready_doc(test_db, test_session.id)

    with patch("app.routers.messages.DashRAGService") as mock_rag:
        async def boom(*args, **kwargs):
            raise RuntimeError("oops")
        mock_rag.return_value.query.side_effect = boom

        with client.stream(
            "POST",
            f"/messages/stream?sid={test_session.id}",
            headers=auth_headers,
            json={"content": "hi"},
        ) as resp:
            assert resp.status_code == 200
            body = "".join([c.decode("utf-8") for c in resp.iter_raw()])

    payload = json.loads([ln for ln in body.splitlines() if ln.startswith("data: ")][0][6:])
    assert payload["type"] == "error"
    assert payload["message"].startswith("Query failed:")
