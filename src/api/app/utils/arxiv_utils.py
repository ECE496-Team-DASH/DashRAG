
from typing import List, Dict
import arxiv

def search_arxiv(query: str, max_results: int = 5) -> List[Dict]:
    search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
    out = []
    for r in search.results():
        out.append({
            "id": r.get_short_id(),
            "title": r.title,
            "authors": ", ".join(a.name for a in r.authors),
            "published": r.published.strftime("%Y-%m-%d") if r.published else None,
            "pdf_url": r.pdf_url
        })
    return out

def download_pdf(arxiv_id: str, out_dir) -> str:
    paper = next(arxiv.Search(id_list=[arxiv_id]).results())
    pdf_path = paper.download_pdf(dirpath=str(out_dir))
    return str(pdf_path)
