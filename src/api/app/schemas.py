
from pydantic import BaseModel, Field
from typing import Optional, Literal

class SessionCreate(BaseModel):
    title: str
    settings: dict | None = None

class SessionOut(BaseModel):
    id: str
    title: str
    settings: dict
    stats: dict | None = None

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
