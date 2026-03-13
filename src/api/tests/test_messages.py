"""
Tests for message endpoints.
"""

from unittest.mock import patch


class TestMessageEndpoints:
    """Tests for /messages endpoints."""

    def test_list_messages_empty(self, client, auth_headers, test_session):
        """Test listing messages in empty session."""
        response = client.get(
            f"/messages?sid={test_session.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json() == []

    def test_list_messages(self, client, auth_headers, test_session, test_db):
        """Test listing messages in session."""
        from app.models import Message, Role
        
        msg = Message(
            session_id=test_session.id,
            role=Role.user,
            content={"text": "Hello"}
        )
        test_db.add(msg)
        test_db.commit()
        
        response = client.get(
            f"/messages?sid={test_session.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["role"] == "user"
        assert data[0]["content"]["text"] == "Hello"

    def test_create_message_requires_ready_document(self, client, auth_headers, test_session):
        """Test that querying requires at least one ready document."""
        response = client.post(
            f"/messages?sid={test_session.id}",
            json={"content": "What is this about?"},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "ready document" in response.json()["detail"].lower()

    def test_create_message_requires_content(self, client, auth_headers, test_session, test_db):
        """Test that message requires content field."""
        from app.models import Document, DocSource, DocStatus
        
        # Add a ready document
        doc = Document(
            session_id=test_session.id,
            source_type=DocSource.upload,
            status=DocStatus.ready,
            title="test.pdf"
        )
        test_db.add(doc)
        test_db.commit()
        
        response = client.post(
            f"/messages?sid={test_session.id}",
            json={},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "content" in response.json()["detail"]


class TestMessageModels:
    """Tests for message model enums."""

    def test_role_values(self):
        """Test Role enum values."""
        from app.models import Role
        
        assert Role.user.value == "user"
        assert Role.assistant.value == "assistant"
        assert Role.tool.value == "tool"
        assert Role.system.value == "system"
