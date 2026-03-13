"""
Pytest configuration and shared fixtures for API tests.
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Mock heavy dependencies before importing app modules
sys.modules['nano_graphrag'] = MagicMock()
sys.modules['nano_graphrag.GraphRAG'] = MagicMock()
sys.modules['nano_graphrag.QueryParam'] = MagicMock()

# Set test environment before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///./test_dashrag.db"
os.environ["DATA_ROOT"] = tempfile.mkdtemp()
os.environ["JWT_SECRET_KEY"] = "test-secret-key"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from passlib.context import CryptContext

from app.db import Base
from app.main import app
from app.models import User, Session, Document, Message, DocSource, DocStatus, Role

# Use a simpler password context for testing to avoid bcrypt issues
test_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=4)


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test."""
    engine = create_engine("sqlite:///./test_dashrag.db", connect_args={"check_same_thread": False})
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with database dependency override."""
    from app.routers import sessions, documents, messages, auth
    
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    # Override the get_db dependency in all routers
    app.dependency_overrides[sessions.get_db] = override_get_db
    app.dependency_overrides[documents.get_db] = override_get_db
    app.dependency_overrides[messages.get_db] = override_get_db
    app.dependency_overrides[auth.get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(test_db):
    """Create a test user."""
    from app.routers.auth import pwd_context
    user = User(
        email="test@example.com",
        hashed_password=pwd_context.hash("testpassword")
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers for a test user."""
    response = client.post(
        "/auth/token",
        data={"username": "test@example.com", "password": "testpassword"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_session(test_db, test_user):
    """Create a test session."""
    session = Session(
        user_id=test_user.id,
        title="Test Session",
        graph_dir=str(Path(os.environ["DATA_ROOT"]) / "sessions" / "1" / "graph")
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)
    return session


@pytest.fixture
def temp_pdf(tmp_path):
    """Create a minimal valid PDF file for testing."""
    import fitz
    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Test content for PDF extraction.")
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path
