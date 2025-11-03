
from pathlib import Path
from typing import Optional, Tuple, List
import fitz  # PyMuPDF

def extract_text(pdf_path: Path, max_pages: Optional[int] = None) -> tuple[str, int]:
    text_parts: List[str] = []
    with fitz.open(pdf_path) as doc:
        pages = len(doc)
        page_limit = min(pages, max_pages) if max_pages else pages
        for page_num in range(page_limit):
            page = doc[page_num]
            page_text = page.get_text()
            if page_text.strip():
                text_parts.append(f"\n--- Page {page_num + 1} ---\n")
                text_parts.append(page_text)
    return ("\n".join(text_parts), pages)
