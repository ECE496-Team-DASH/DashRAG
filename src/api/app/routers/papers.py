
from fastapi import APIRouter
from ..utils.arxiv_utils import search_arxiv

router = APIRouter(
    prefix="/papers", 
    tags=["papers"]
)

@router.get(
    "/search", 
    response_model=list[dict],
    summary="Search arXiv papers (global)",
    description="""
    Search arXiv papers without being tied to a specific session.
    
    **Use cases:**
    - Browse papers before creating a session
    - General research exploration
    - Find papers to add to multiple sessions
    
    **Query parameters:**
    - `query` (required): Search terms (e.g., "machine learning healthcare")
    - `max_results` (optional, default=10): Maximum papers to return
    
    **Search tips:**
    - Use specific terms: "transformer attention" vs "AI"
    - Combine topics: "reinforcement learning robotics"
    - Author names: "Yoshua Bengio"
    - arXiv categories: "cs.AI", "cs.LG"
    
    **Returns:** Array of paper metadata from arXiv API
    
    **Note:** This endpoint doesn't add papers to any session. Use:
    - `POST /sessions/{sid}/documents/add-arxiv` to add to a session
    - `GET /sessions/{sid}/documents/search-arxiv` for session-scoped search
    """,
    responses={
        200: {
            "description": "Search results from arXiv",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "arxiv_id": "1706.03762",
                            "title": "Attention Is All You Need",
                            "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
                            "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
                            "published_at": "2017-06-12",
                            "pdf_url": "http://arxiv.org/pdf/1706.03762"
                        },
                        {
                            "arxiv_id": "1810.04805",
                            "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
                            "authors": ["Jacob Devlin", "Ming-Wei Chang"],
                            "abstract": "We introduce a new language representation model called BERT...",
                            "published_at": "2018-10-11",
                            "pdf_url": "http://arxiv.org/pdf/1810.04805"
                        }
                    ]
                }
            }
        }
    }
)
def papers_search(query: str, max_results: int = 10):
    """Search arXiv papers globally (not session-specific)"""
    return search_arxiv(query, max_results=max_results)
