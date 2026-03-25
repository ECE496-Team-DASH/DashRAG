from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Enum, ForeignKey, JSON, Text, Integer, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
import enum

from .db import Base

class DocSource(str, enum.Enum):
    upload = "upload"
    arxiv = "arxiv"

class DocStatus(str, enum.Enum):
    pending = "pending"
    downloading = "downloading"
    inserting = "inserting"
    ready = "ready"
    error = "error"

class ProcessingPhase(str, enum.Enum):
    pdf_extraction = "pdf_extraction"
    text_chunking = "text_chunking"
    entity_extraction = "entity_extraction"
    graph_clustering = "graph_clustering"
    community_reports = "community_reports"
    finalizing = "finalizing"

class Role(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    tool = "tool"
    system = "system"

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    graph_dir: Mapped[str] = mapped_column(String, nullable=False)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="sessions")
    documents = relationship("Document", back_populates="session", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[DocSource] = mapped_column(Enum(DocSource), nullable=False)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    arxiv_id: Mapped[str | None] = mapped_column(String, nullable=True)
    authors: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[str | None] = mapped_column(String, nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(String, nullable=True)
    local_pdf_path: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[DocStatus] = mapped_column(Enum(DocStatus), default=DocStatus.pending)
    processing_phase: Mapped[str | None] = mapped_column(String, nullable=True)
    progress_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    insert_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    session = relationship("Session", back_populates="documents")

    __table_args__ = (
        # Speeds up listing & status-filtering documents within a session
        Index("ix_documents_session_status", "session_id", "status"),
    )

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    token_usage: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc))

    session = relationship("Session", back_populates="messages")

    __table_args__ = (
        # Speeds up fetching conversation history ordered by time within a session
        Index("ix_messages_session_created", "session_id", "created_at"),
    )
