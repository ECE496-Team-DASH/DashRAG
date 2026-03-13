"""
Tests for document endpoints.
"""

from unittest.mock import patch, Mock


class TestDocumentEndpoints:
    """Tests for /documents endpoints."""

    def test_list_documents_empty(self, client, auth_headers, test_session):
        """Test listing documents in empty session."""
        response = client.get(
            f"/documents?sid={test_session.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json() == []

    def test_list_documents(self, client, auth_headers, test_session, test_db):
        """Test listing documents in session."""
        from app.models import Document, DocSource, DocStatus
        
        doc = Document(
            session_id=test_session.id,
            source_type=DocSource.upload,
            status=DocStatus.ready,
            title="test.pdf"
        )
        test_db.add(doc)
        test_db.commit()
        
        response = client.get(
            f"/documents?sid={test_session.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "test.pdf"

    def test_upload_pdf_rejects_non_pdf(self, client, auth_headers, test_session):
        """Test that non-PDF uploads are rejected."""
        response = client.post(
            f"/documents/upload?sid={test_session.id}",
            files={"file": ("test.txt", b"not a pdf", "text/plain")},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "PDF" in response.json()["detail"]

    def test_upload_pdf_requires_auth(self, client, test_session):
        """Test that upload requires authentication."""
        response = client.post(
            f"/documents/upload?sid={test_session.id}",
            files={"file": ("test.pdf", b"fake pdf", "application/pdf")}
        )
        
        assert response.status_code == 401

    @patch('app.routers.documents.search_arxiv')
    def test_search_arxiv(self, mock_search, client, auth_headers, test_session):
        """Test arXiv search endpoint."""
        mock_search.return_value = [
            {"arxiv_id": "2301.00001", "title": "Test Paper"}
        ]
        
        response = client.get(
            f"/documents/search-arxiv?sid={test_session.id}&query=transformers",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["arxiv_id"] == "2301.00001"

    def test_add_arxiv_requires_arxiv_id(self, client, auth_headers, test_session):
        """Test that add-arxiv requires arxiv_id."""
        response = client.post(
            f"/documents/add-arxiv?sid={test_session.id}",
            json={},
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "arxiv_id" in response.json()["detail"]


class TestDocumentModels:
    """Tests for document model enums."""

    def test_doc_source_values(self):
        """Test DocSource enum values."""
        from app.models import DocSource
        
        assert DocSource.upload.value == "upload"
        assert DocSource.arxiv.value == "arxiv"

    def test_doc_status_values(self):
        """Test DocStatus enum values."""
        from app.models import DocStatus
        
        assert DocStatus.pending.value == "pending"
        assert DocStatus.downloading.value == "downloading"
        assert DocStatus.inserting.value == "inserting"
        assert DocStatus.ready.value == "ready"
        assert DocStatus.error.value == "error"

    def test_processing_phase_values(self):
        """Test ProcessingPhase enum values."""
        from app.models import ProcessingPhase
        
        assert ProcessingPhase.pdf_extraction.value == "pdf_extraction"
        assert ProcessingPhase.entity_extraction.value == "entity_extraction"
