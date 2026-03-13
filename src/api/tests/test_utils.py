"""
Tests for utility functions (pdf_utils, arxiv_utils, locks).
"""

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile


class TestPdfUtils:
    """Tests for PDF extraction utilities."""

    def test_extract_text_returns_text_and_page_count(self, temp_pdf):
        """Test that extract_text returns text content and page count."""
        from app.utils.pdf_utils import extract_text
        
        text, pages = extract_text(temp_pdf)
        
        assert pages == 1
        assert "Test content" in text
        assert "Page 1" in text

    def test_extract_text_with_max_pages(self, tmp_path):
        """Test that max_pages limits extraction."""
        import fitz
        from app.utils.pdf_utils import extract_text
        
        # Create a 3-page PDF
        pdf_path = tmp_path / "multi_page.pdf"
        doc = fitz.open()
        for i in range(3):
            page = doc.new_page()
            page.insert_text((50, 50), f"Page {i+1} content")
        doc.save(str(pdf_path))
        doc.close()
        
        text, pages = extract_text(pdf_path, max_pages=2)
        
        assert pages == 3  # Total pages in document
        assert "Page 1" in text
        assert "Page 2" in text
        assert "Page 3" not in text  # Should be limited

    def test_extract_text_empty_pdf(self, tmp_path):
        """Test extraction from PDF with no text."""
        import fitz
        from app.utils.pdf_utils import extract_text
        
        pdf_path = tmp_path / "empty.pdf"
        doc = fitz.open()
        doc.new_page()  # Empty page
        doc.save(str(pdf_path))
        doc.close()
        
        text, pages = extract_text(pdf_path)
        
        assert pages == 1
        assert text.strip() == ""


class TestArxivUtils:
    """Tests for arXiv utilities."""

    @patch('app.utils.arxiv_utils.arxiv.Search')
    def test_search_arxiv_returns_results(self, mock_search):
        """Test that search_arxiv returns formatted results."""
        from app.utils.arxiv_utils import search_arxiv
        from datetime import datetime
        
        # Mock arXiv result with proper author objects
        mock_author = Mock()
        mock_author.name = "Author One"
        
        mock_result = Mock()
        mock_result.get_short_id.return_value = "2301.00001"
        mock_result.title = "Test Paper"
        mock_result.authors = [mock_author]
        mock_result.summary = "Test abstract"
        mock_result.published = datetime(2023, 1, 1)
        mock_result.pdf_url = "https://arxiv.org/pdf/2301.00001"
        
        mock_search.return_value.results.return_value = [mock_result]
        
        results = search_arxiv("test query", max_results=1)
        
        assert len(results) == 1
        assert results[0]["arxiv_id"] == "2301.00001"
        assert results[0]["title"] == "Test Paper"
        assert "2023-01-01" in results[0]["published_at"]

    @patch('app.utils.arxiv_utils.arxiv.Search')
    def test_search_arxiv_empty_results(self, mock_search):
        """Test search with no results."""
        from app.utils.arxiv_utils import search_arxiv
        
        mock_search.return_value.results.return_value = []
        
        results = search_arxiv("nonexistent query")
        
        assert results == []


class TestLocks:
    """Tests for file locking utilities."""

    def test_session_lock_creates_lock_file(self, tmp_path):
        """Test that session_lock creates the lock file."""
        from app.utils.locks import session_lock
        
        lock_file = tmp_path / "subdir" / ".lock"
        
        with session_lock(lock_file):
            assert lock_file.exists()

    def test_session_lock_allows_sequential_access(self, tmp_path):
        """Test that lock can be acquired sequentially."""
        from app.utils.locks import session_lock
        
        lock_file = tmp_path / ".lock"
        results = []
        
        with session_lock(lock_file):
            results.append(1)
        
        with session_lock(lock_file):
            results.append(2)
        
        assert results == [1, 2]
