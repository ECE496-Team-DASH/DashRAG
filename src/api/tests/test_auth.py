"""
Tests for authentication endpoints and utilities.
"""

from jose import jwt


class TestAuthEndpoints:
    """Tests for /auth endpoints."""

    def test_register_creates_user(self, client):
        """Test user registration."""
        response = client.post(
            "/auth/register",
            json={"email": "new@example.com", "password": "newpassword"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "new@example.com"
        assert "id" in data

    def test_register_duplicate_email_fails(self, client, test_user):
        """Test that duplicate email registration fails."""
        response = client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "password"}
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_missing_fields_fails(self, client):
        """Test that registration without required fields fails."""
        response = client.post("/auth/register", json={"email": "test@example.com"})
        
        assert response.status_code == 400

    def test_login_returns_token(self, client, test_user):
        """Test successful login returns JWT token."""
        response = client.post(
            "/auth/token",
            data={"username": "test@example.com", "password": "testpassword"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials_fails(self, client, test_user):
        """Test login with wrong password fails."""
        response = client.post(
            "/auth/token",
            data={"username": "test@example.com", "password": "wrongpassword"}
        )
        
        assert response.status_code == 400

    def test_login_nonexistent_user_fails(self, client):
        """Test login with non-existent user fails."""
        response = client.post(
            "/auth/token",
            data={"username": "nonexistent@example.com", "password": "password"}
        )
        
        assert response.status_code == 400

    def test_token_contains_user_id(self, client, test_user):
        """Test that JWT token contains user ID."""
        from app.config import settings
        
        response = client.post(
            "/auth/token",
            data={"username": "test@example.com", "password": "testpassword"}
        )
        
        token = response.json()["access_token"]
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        
        assert payload["sub"] == str(test_user.id)
