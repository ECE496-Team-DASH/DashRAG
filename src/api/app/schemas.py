
from pydantic import BaseModel, Field
from typing import Optional, Literal

class SessionCreate(BaseModel):
    title: str
    settings: dict | None = None

class SessionOut(BaseModel):
    id: int
    title: str
    settings: dict
    stats: dict | None = None

class DocumentResponse(BaseModel):
    id: int
    session_id: int
    source_type: str
    title: str | None
    status: str
    processing_phase: str | None = None
    progress_percent: int | None = None
    arxiv_id: str | None = None
    authors: str | None = None
    published_at: str | None = None
    pages: int | None = None
    created_at: str

    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    content: str
    mode: Literal["local","global","naive"] | None = None
    top_k: int | None = None
    level: int | None = None
    response_type: str | None = None
    only_need_context: bool = False
    include_text_chunks_in_context: bool | None = None
    global_max_consider_community: int | None = None
    global_min_community_rating: int | None = None
    naive_max_token_for_text_unit: int | None = None
