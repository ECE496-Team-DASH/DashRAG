"""
Tests for health endpoint.
"""


class TestHealthEndpoint:
    """Tests for /healthz endpoint."""

    def test_health_check(self, client):
        """Test health check returns ok status."""
        response = client.get("/healthz")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "data_root" in data
        assert "free_space_mb" in data
