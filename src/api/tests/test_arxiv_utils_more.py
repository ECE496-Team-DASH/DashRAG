"""Additional tests for arXiv utils."""

from unittest.mock import Mock, patch


@patch("app.utils.arxiv_utils.requests.head")
@patch("app.utils.arxiv_utils.arxiv.Search")
def test_search_arxiv_includes_pdf_size_mb(mock_search, mock_head):
    from app.utils.arxiv_utils import search_arxiv
    from datetime import datetime

    # Mock HEAD with content-length
    resp = Mock()
    resp.status_code = 200
    resp.headers = {"content-length": str(5 * 1024 * 1024)}
    mock_head.return_value = resp

    author = Mock(); author.name = "A"
    result = Mock()
    result.get_short_id.return_value = "1234.5678"
    result.title = "T"
    result.authors = [author]
    result.summary = "S"
    result.published = datetime(2020, 1, 2)
    result.pdf_url = "https://arxiv.org/pdf/1234.5678"

    mock_search.return_value.results.return_value = [result]

    out = search_arxiv("q", max_results=1)
    assert out[0]["pdf_size_mb"] == 5.0


@patch("app.utils.arxiv_utils.requests.head")
@patch("app.utils.arxiv_utils.arxiv.Search")
def test_search_arxiv_head_failure_omits_pdf_size(mock_search, mock_head):
    from app.utils.arxiv_utils import search_arxiv

    mock_head.side_effect = Exception("network")

    author = Mock(); author.name = "A"
    result = Mock()
    result.get_short_id.return_value = "1234.5678"
    result.title = "T"
    result.authors = [author]
    result.summary = "S"
    result.published = None
    result.pdf_url = "https://arxiv.org/pdf/1234.5678"

    mock_search.return_value.results.return_value = [result]

    out = search_arxiv("q", max_results=1)
    assert out[0]["pdf_size_mb"] is None
    assert out[0]["published_at"] is None
