from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

class Base(DeclarativeBase):
    pass

_is_sqlite = settings.database_url.startswith("sqlite")

# PostgreSQL: larger pool to serve concurrent requests and multiple background threads.
# SQLite: no pool settings (StaticPool or NullPool would be needed, but defaults work for dev).
_engine_kwargs: dict = {"connect_args": {"check_same_thread": False}} if _is_sqlite else {
    "pool_size": 10,       # Maintain up to 10 persistent connections
    "max_overflow": 20,    # Allow up to 20 additional overflow connections under load
    "pool_timeout": 30,    # Wait at most 30s for a connection before raising
    "pool_recycle": 1800,  # Recycle connections every 30 min (avoids Cloud SQL idle timeouts)
    "pool_pre_ping": True, # Verify connection health before each use (avoids stale socket errors)
}

engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def init_db():
    """Initialize database tables. Call this after all models are imported."""
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _ensure_indexes()


def _ensure_indexes():
    """Create performance indexes on existing tables if they are missing.

    Uses IF NOT EXISTS so this is safe to run on every startup, including
    against production databases that were created before these indexes existed.
    Both SQLite and PostgreSQL (>=9.5) support this syntax.
    """
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    with engine.connect() as conn:
        if "messages" in insp.get_table_names():
            existing = {i["name"] for i in insp.get_indexes("messages")}
            if "ix_messages_session_created" not in existing:
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_messages_session_created "
                    "ON messages (session_id, created_at)"
                ))
        if "documents" in insp.get_table_names():
            existing = {i["name"] for i in insp.get_indexes("documents")}
            if "ix_documents_session_status" not in existing:
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_documents_session_status "
                    "ON documents (session_id, status)"
                ))
        conn.commit()
