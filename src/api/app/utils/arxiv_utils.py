
from typing import List, Dict
import arxiv
import requests

def search_arxiv(query: str, max_results: int = 5) -> List[Dict]:
    search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
    out = []
    for r in search.results():
        # Get PDF size via HEAD request
        pdf_size_mb = None
        try:
            response = requests.head(r.pdf_url, timeout=5, allow_redirects=True)
            if response.status_code == 200 and 'content-length' in response.headers:
                size_bytes = int(response.headers['content-length'])
                pdf_size_mb = round(size_bytes / (1024 * 1024), 2)  # Convert to MB
        except Exception:
            pass  # If size check fails, just omit it
        
        out.append({
            "arxiv_id": r.get_short_id(),
            "title": r.title,
            "authors": ", ".join(a.name for a in r.authors),
            "abstract": r.summary,
            "published_at": r.published.strftime("%Y-%m-%d") if r.published else None,
            "pdf_url": r.pdf_url,
            "pdf_size_mb": pdf_size_mb
        })
    return out

def download_pdf(arxiv_id: str, out_dir) -> str:
    paper = next(arxiv.Search(id_list=[arxiv_id]).results())
    pdf_path = paper.download_pdf(dirpath=str(out_dir))
    return str(pdf_path)
