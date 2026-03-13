"""Unit tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError


def test_session_create_requires_title():
    from app.schemas import SessionCreate

    with pytest.raises(ValidationError):
        SessionCreate()


def test_session_create_accepts_optional_settings():
    from app.schemas import SessionCreate

    s = SessionCreate(title="t", settings={"a": 1})
    assert s.title == "t"
    assert s.settings == {"a": 1}


def test_session_out_requires_settings_and_serializes_stats_optional():
    from app.schemas import SessionOut

    out = SessionOut(id=1, title="T", settings={}, stats=None)
    assert out.id == 1
    assert out.stats is None


def test_document_response_from_attributes():
    from app.schemas import DocumentResponse

    class Obj:
        def __init__(self):
            self.id = 1
            self.session_id = 2
            self.source_type = "upload"
            self.title = "x.pdf"
            self.status = "ready"
            self.processing_phase = None
            self.progress_percent = None
            self.arxiv_id = None
            self.authors = None
            self.published_at = None
            self.pages = 3
            self.created_at = "2026-01-01T00:00:00"

    o = Obj()
    m = DocumentResponse.model_validate(o)
    assert m.id == 1
    assert m.pages == 3


def test_chat_request_valid_and_invalid_mode():
    from app.schemas import ChatRequest

    ok = ChatRequest(content="hi", mode="local", top_k=5)
    assert ok.mode == "local"

    with pytest.raises(ValidationError):
        ChatRequest(content="hi", mode="bogus")
