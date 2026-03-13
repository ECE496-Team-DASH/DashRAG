"""
Tests for session endpoints.
"""


class TestSessionEndpoints:
    """Tests for /sessions endpoints."""

    def test_create_session(self, client, auth_headers):
        """Test creating a new session."""
        response = client.post(
            "/sessions",
            json={"title": "My Research Session"},
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "My Research Session"
        assert "id" in data

    def test_create_session_default_title(self, client, auth_headers):
        """Test creating session without title uses default."""
        response = client.post("/sessions", json={}, headers=auth_headers)
        
        assert response.status_code == 201
        assert response.json()["title"] == "New Session"

    def test_create_session_requires_auth(self, client):
        """Test that creating session requires authentication."""
        response = client.post("/sessions", json={"title": "Test"})
        
        assert response.status_code == 401

    def test_list_sessions(self, client, auth_headers, test_session):
        """Test listing user sessions."""
        response = client.get("/sessions", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(s["id"] == test_session.id for s in data)

    def test_get_session_detail(self, client, auth_headers, test_session):
        """Test getting session details."""
        response = client.get(
            f"/sessions/detail?sid={test_session.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_session.id
        assert data["title"] == test_session.title

    def test_get_session_not_found(self, client, auth_headers):
        """Test getting non-existent session."""
        response = client.get("/sessions/detail?sid=99999", headers=auth_headers)
        
        assert response.status_code == 404

    def test_update_session(self, client, auth_headers, test_session):
        """Test updating session title."""
        response = client.patch(
            f"/sessions?sid={test_session.id}",
            json={"title": "Updated Title"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    def test_delete_session(self, client, auth_headers, test_session):
        """Test deleting a session."""
        response = client.delete(
            f"/sessions?sid={test_session.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["ok"] is True
        
        # Verify session is deleted
        response = client.get(
            f"/sessions/detail?sid={test_session.id}",
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_cannot_access_other_user_session(self, client, test_db, test_session):
        """Test that users cannot access other users' sessions."""
        from app.models import User
        from app.routers.auth import pwd_context
        
        # Create another user
        other_user = User(
            email="other@example.com",
            hashed_password=pwd_context.hash("password")
        )
        test_db.add(other_user)
        test_db.commit()
        
        # Login as other user
        response = client.post(
            "/auth/token",
            data={"username": "other@example.com", "password": "password"}
        )
        other_headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
        
        # Try to access first user's session
        response = client.get(
            f"/sessions/detail?sid={test_session.id}",
            headers=other_headers
        )
        
        assert response.status_code == 403
