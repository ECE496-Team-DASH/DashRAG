
from pathlib import Path
from typing import Optional, List, Any
import os
import logging
import csv
import io
import re

from nano_graphrag import GraphRAG, QueryParam
from ..config import settings

logger = logging.getLogger(__name__)


def _resolve_session_id_from_working_dir(working_dir: Path) -> int | None:
    # Expected shape: .../data/sessions/{sid}/graph
    parts = list(working_dir.parts)
    try:
        sessions_idx = parts.index("sessions")
    except ValueError:
        return None
    if sessions_idx + 1 >= len(parts):
        return None
    sid_raw = parts[sessions_idx + 1]
    if sid_raw.isdigit():
        return int(sid_raw)
    return None


def _load_session_document_filenames(session_id: int) -> list[str]:
    if session_id <= 0:
        return []

    try:
        from ..db import SessionLocal
        from ..models import Document
    except Exception:
        return []

    db = SessionLocal()
    try:
        docs = (
            db.query(Document)
            .filter(Document.session_id == session_id)
            .order_by(Document.created_at.asc())
            .all()
        )

        filenames: list[str] = []
        for doc in docs:
            if doc.title:
                filenames.append(str(doc.title))
            elif doc.local_pdf_path:
                filenames.append(Path(doc.local_pdf_path).name)
        return [name for name in filenames if name]
    except Exception:
        logger.warning("Failed loading document filenames for session %s", session_id, exc_info=True)
        return []
    finally:
        db.close()


def _enrich_document_citations_with_filenames(
    citations: list[dict[str, Any]], working_dir: Path
) -> list[dict[str, Any]]:
    session_id = _resolve_session_id_from_working_dir(working_dir)
    if session_id is None:
        return citations

    filenames = _load_session_document_filenames(session_id)
    if not filenames:
        return citations

    # If there is one uploaded document in the session, it is the authoritative display name.
    preferred_name = filenames[-1] if len(filenames) == 1 else None

    enriched: list[dict[str, Any]] = []
    for citation in citations:
        if not isinstance(citation, dict):
            enriched.append(citation)
            continue

        ctype = citation.get("type")
        if ctype != "document":
            enriched.append(citation)
            continue

        updated = dict(citation)
        metadata = dict(updated.get("metadata") or {})
        display_name = preferred_name or metadata.get("file_name") or updated.get("label")
        if isinstance(display_name, str) and display_name:
            updated["label"] = display_name
            metadata["file_name"] = display_name
        updated["metadata"] = metadata
        enriched.append(updated)

    return enriched


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_csv_cell(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().strip("\ufeff")
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        text = text[1:-1]
    return text.replace('""', '"').strip()


def _normalize_snippet(value: Any, max_len: int = 320) -> str:
    compact = re.sub(r"\s+", " ", _normalize_csv_cell(value)).strip()
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 3].rstrip() + "..."


def _citation_id(prefix: str, raw_id: Any, fallback_index: int) -> str:
    candidate = _normalize_csv_cell(raw_id)
    if not candidate or len(candidate) > 80 or re.search(r"\s", candidate):
        candidate = str(fallback_index)
    candidate = re.sub(r"[^A-Za-z0-9_.:-]+", "-", candidate).strip("-") or str(fallback_index)
    return f"{prefix}-{candidate}"


def _display_doc_label(doc_id: str) -> str:
    normalized = _normalize_csv_cell(doc_id)
    if not normalized:
        return "Document"
    if len(normalized) <= 48:
        return normalized
    return f"...{normalized[-45:]}"


def _parse_csv_section(context: str, section_name: str) -> list[dict[str, str]]:
    pattern = rf"-----{re.escape(section_name)}-----\s*```csv\s*(.*?)\s*```"
    match = re.search(pattern, context, flags=re.DOTALL)
    if not match:
        return []

    payload = match.group(1).strip()
    if not payload:
        return []

    # nano-graphrag emits comma+tab separators in CSV sections.
    normalized_payload = payload.replace(",\t", ",")
    reader = csv.DictReader(
        io.StringIO(normalized_payload),
        delimiter=",",
        quotechar='"',
        skipinitialspace=True,
    )

    rows: list[dict[str, str]] = []
    for raw_row in reader:
        if not raw_row:
            continue

        row: dict[str, str] = {}
        for key, value in raw_row.items():
            if key is None:
                continue
            normalized_key = _normalize_csv_cell(key).lower()
            if not normalized_key:
                continue
            row[normalized_key] = _normalize_csv_cell(value)

        if row:
            rows.append(row)
    return rows


def _extract_local_citations(context: str) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    document_counts: dict[str, int] = {}

    community_rows = _parse_csv_section(context, "Reports")
    entity_rows = _parse_csv_section(context, "Entities")
    relationship_rows = _parse_csv_section(context, "Relationships")
    source_rows = _parse_csv_section(context, "Sources")

    logger.info(
        "Local citation section counts: reports=%d entities=%d relationships=%d sources=%d",
        len(community_rows),
        len(entity_rows),
        len(relationship_rows),
        len(source_rows),
    )

    for idx, row in enumerate(community_rows):
        report = _normalize_snippet(row.get("content", ""))
        label = _normalize_csv_cell(row.get("title")) or "Community summary"
        score = _safe_float(row.get("rating"), 0.0)
        occurrence = _safe_float(row.get("occurrence"), 0.0)
        citations.append(
            {
                "id": _citation_id("community", row.get("id"), idx),
                "type": "community",
                "label": label,
                "snippet": report or label,
                "score": score,
                "metadata": {
                    "occurrence": occurrence,
                    "community_id": _normalize_csv_cell(row.get("id")),
                },
            }
        )

    for idx, row in enumerate(entity_rows):
        entity = _normalize_csv_cell(row.get("entity")) or "Entity"
        entity_type = _normalize_csv_cell(row.get("type")) or "UNKNOWN"
        snippet = _normalize_snippet(row.get("description", ""))
        citations.append(
            {
                "id": _citation_id("entity", row.get("id"), idx),
                "type": "entity",
                "label": entity,
                "snippet": snippet,
                "score": _safe_float(row.get("rank"), 0.0),
                "metadata": {
                    "entity_type": entity_type,
                },
            }
        )

    for idx, row in enumerate(relationship_rows):
        source = _normalize_csv_cell(row.get("source")) or "UNKNOWN"
        target = _normalize_csv_cell(row.get("target")) or "UNKNOWN"
        citations.append(
            {
                "id": _citation_id("relationship", row.get("id"), idx),
                "type": "relationship",
                "label": f"{source} -> {target}",
                "snippet": _normalize_snippet(row.get("description", "")),
                "score": _safe_float(row.get("rank"), 0.0),
                "metadata": {
                    "weight": _safe_float(row.get("weight"), 0.0),
                },
            }
        )

    for idx, row in enumerate(source_rows):
        full_doc_id = _normalize_csv_cell(row.get("full_doc_id")) or "UNKNOWN"
        if full_doc_id and full_doc_id != "UNKNOWN":
            document_counts[full_doc_id] = document_counts.get(full_doc_id, 0) + 1

        chunk_order = _normalize_csv_cell(row.get("chunk_order_index")) or "?"
        chunk_snippet = _normalize_snippet(row.get("content"))
        chunk_label = f"{_display_doc_label(full_doc_id)} | chunk {chunk_order}"

        citations.append(
            {
                "id": _citation_id("chunk", row.get("id"), idx),
                "type": "text_chunk",
                "label": chunk_label,
                "snippet": chunk_snippet,
                "metadata": {
                    "full_doc_id": full_doc_id,
                    "chunk_order_index": chunk_order,
                },
            }
        )

    # Promote frequently used document IDs as top-level citations.
    for doc_id, count in sorted(document_counts.items(), key=lambda item: item[1], reverse=True):
        citations.append(
            {
                "id": f"document-{doc_id}",
                "type": "document",
                "label": _display_doc_label(doc_id),
                "snippet": f"Referenced by {count} retrieved text chunk(s).",
                "score": float(count),
                "metadata": {
                    "full_doc_id": doc_id,
                    "chunk_count": count,
                },
            }
        )

    return citations


def _extract_global_citations(context: str) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    pattern = r"----Analyst\s+(\d+)----\s*\nImportance Score:\s*([\d\.\-]+)\s*\n(.*?)(?=\n----Analyst\s+\d+----|$)"
    for match in re.finditer(pattern, context, flags=re.DOTALL):
        analyst_id, score_str, body = match.groups()
        citations.append(
            {
                "id": f"community-analyst-{analyst_id}",
                "type": "community",
                "label": f"Analyst {analyst_id}",
                "snippet": _normalize_snippet(body),
                "score": _safe_float(score_str, 0.0),
            }
        )
    return citations


def _extract_naive_citations(context: str) -> list[dict[str, Any]]:
    chunks = [part.strip() for part in context.split("--New Chunk--") if part.strip()]
    citations: list[dict[str, Any]] = []
    for idx, chunk in enumerate(chunks):
        citations.append(
            {
                "id": f"chunk-{idx}",
                "type": "text_chunk",
                "label": f"Chunk {idx + 1}",
                "snippet": _normalize_snippet(chunk),
            }
        )
    return citations


def _rank_and_trim_citations(citations: list[dict[str, Any]], max_items: int = 40) -> list[dict[str, Any]]:
    type_priority = {
        "document": 0,
        "community": 1,
        "entity": 2,
        "relationship": 3,
        "text_chunk": 4,
    }

    per_type_cap = {
        "document": 8,
        "community": 6,
        "entity": 10,
        "relationship": 10,
        "text_chunk": 12,
    }

    sanitized: list[dict[str, Any]] = []
    for item in citations:
        if not isinstance(item, dict):
            continue

        item_type = item.get("type", "text_chunk")
        snippet = _normalize_snippet(item.get("snippet", ""))
        label = _normalize_csv_cell(item.get("label")) or item_type.title()

        if item_type == "community" and not snippet:
            # Skip empty community summaries to avoid unreadable noise.
            continue

        if item_type != "document" and not snippet:
            continue

        enriched = {
            **item,
            "type": item_type,
            "label": label,
            "snippet": snippet,
            "score": _safe_float(item.get("score"), 0.0),
        }
        sanitized.append(enriched)

    by_type: dict[str, list[dict[str, Any]]] = {}
    for item in sanitized:
        by_type.setdefault(item["type"], []).append(item)

    selected: list[dict[str, Any]] = []
    for citation_type, items in by_type.items():
        ranked_type = sorted(
            items,
            key=lambda item: (
                -_safe_float(item.get("score"), 0.0),
                -len(item.get("snippet", "") or ""),
            ),
        )
        selected.extend(ranked_type[: per_type_cap.get(citation_type, 6)])

    ranked = sorted(
        selected,
        key=lambda item: (
            type_priority.get(item.get("type", "text_chunk"), 99),
            -_safe_float(item.get("score"), 0.0),
        ),
    )
    return ranked[:max_items]


def _build_citations(mode: str, contexts: list[Any]) -> list[dict[str, Any]]:
    if not contexts:
        return []

    raw_context = contexts[0]
    if not isinstance(raw_context, str):
        return []

    if mode == "local":
        citations = _extract_local_citations(raw_context)
    elif mode == "global":
        citations = _extract_global_citations(raw_context)
    elif mode == "naive":
        citations = _extract_naive_citations(raw_context)
    else:
        citations = []

    return _rank_and_trim_citations(citations)

def resolve_provider_kwargs() -> dict:
    """
    Resolve LLM provider configuration for nano-graphrag.
    
    Returns only boolean flags (using_gemini, using_azure_openai).
    The GraphRAG.__post_init__ method will automatically set the appropriate
    model functions based on these flags.
    
    DO NOT pass model functions directly - this causes initialization errors!
    """
    use_gemini = settings.ngr_use_gemini
    use_azure = settings.ngr_use_azure_openai
    
    if use_gemini is None:
        use_gemini = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
    if use_azure is None:
        use_azure = bool(os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"))

    if use_azure:
        logger.info("Using Azure OpenAI for GraphRAG")
        return dict(using_azure_openai=True)
    if use_gemini:
        logger.info("Using Gemini for GraphRAG")
        return dict(using_gemini=True)
    
    # Default to OpenAI-compatible (via environment variables)
    logger.info("Using OpenAI for GraphRAG")
    return dict()

class DashRAGService:
    def __init__(self, working_dir: Path):
        self.working_dir = working_dir
        self.working_dir.mkdir(parents=True, exist_ok=True)
        
        provider_kwargs = resolve_provider_kwargs()
        logger.info(f"Initializing GraphRAG in {working_dir} with config: {provider_kwargs}")
        
        # Explicitly verify and set GEMINI_API_KEY in environment
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        logger.info(f"GEMINI_API_KEY status: {'SET (len=' + str(len(gemini_key)) + ')' if gemini_key else 'NOT SET'}")
        
        if not gemini_key and provider_kwargs.get('using_gemini'):
            # Try to get from settings
            from ..config import settings
            if settings.gemini_api_key:
                os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
                gemini_key = settings.gemini_api_key
                logger.info(f"Set GEMINI_API_KEY from settings (len={len(settings.gemini_api_key)})")
            else:
                logger.error("GEMINI_API_KEY not found in environment or settings!")
        
        # Log first/last chars for debugging (without exposing full key)
        if gemini_key:
            logger.info(f"API Key verification: starts with '{gemini_key[:10]}...', ends with '...{gemini_key[-5:]}'")
        
        # CRITICAL: Reset the global Gemini client so it picks up the new API key
        if provider_kwargs.get('using_gemini'):
            try:
                from nano_graphrag import _llm
                import google.genai as genai
                
                # Force reset both nano-graphrag's client AND google.genai's internal cache
                _llm.global_gemini_client = None
                
                # Manually create and set the client with explicit API key
                if gemini_key:
                    _llm.global_gemini_client = genai.Client(api_key=gemini_key)
                    logger.info(f"Created new Gemini client with explicit API key")
                else:
                    logger.error("Cannot create Gemini client - no API key available!")
                    
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}", exc_info=True)
                raise
        
        try:
            self.rag = GraphRAG(
                working_dir=str(self.working_dir),
                always_create_working_dir=True,
                enable_llm_cache=True,
                # Enable GenKG extraction for controlled entity limits
                use_genkg_extraction=True,
                genkg_node_limit=25,  # Limit entities per document
                genkg_create_visualization=False,  # Set to True if you want HTML visualizations
                **provider_kwargs
            )
            logger.info("GraphRAG initialized successfully with GenKG extraction (25 nodes per document)")
        except Exception as e:
            logger.error(f"Failed to initialize GraphRAG: {e}", exc_info=True)
            raise

    async def insert_texts(self, texts: List[str] | str) -> None:
        """Insert text(s) into the knowledge graph"""
        logger.info(f"Inserting {'single document' if isinstance(texts, str) else f'{len(texts)} documents'} into GraphRAG")
        
        try:
            await self.rag.ainsert(texts)
            logger.info("Text insertion completed successfully")
        except Exception as e:
            logger.error(f"Failed to insert texts into GraphRAG: {e}", exc_info=True)
            raise

    async def query(self, prompt: str, **qp_kwargs) -> dict[str, Any]:
        """Query the knowledge graph"""
        cleaned_kwargs = {k: v for k, v in qp_kwargs.items() if v is not None}
        if "include_text_chunks_in_context" in cleaned_kwargs:
            cleaned_kwargs["include_text_chunks"] = cleaned_kwargs.pop("include_text_chunks_in_context")

        if cleaned_kwargs.get("mode", "global") == "local" and "include_text_chunks" not in cleaned_kwargs:
            cleaned_kwargs["include_text_chunks"] = True

        cleaned_kwargs["return_context"] = True
        qp = QueryParam(**cleaned_kwargs)
        logger.info(f"Querying GraphRAG with mode: {qp.mode}")
        try:
            result = await self.rag.aquery(prompt, qp)
            if isinstance(result, tuple):
                answer, contexts = result
            else:
                answer, contexts = result, []

            citations = _build_citations(qp.mode, contexts)
            citations = _enrich_document_citations_with_filenames(citations, self.working_dir)
            logger.info("Query completed successfully")
            return {
                "text": answer,
                "citations": citations,
            }
        except AssertionError as e:
            # Handle JSON parsing errors from LLM responses
            error_msg = str(e)
            if "Unable to parse JSON from response" in error_msg:
                # Extract the actual LLM response from the error message
                if "response: " in error_msg:
                    llm_response = error_msg.split("response: ", 1)[1]
                    logger.warning(f"LLM returned non-JSON response, using it directly: {llm_response[:100]}...")
                    return {"text": llm_response, "citations": []}
                else:
                    logger.error(f"Could not extract LLM response from error: {error_msg}")
                    raise ValueError("The AI model returned an invalid response format. Please try again or rephrase your question.")
            else:
                # Re-raise if it's a different assertion error
                raise
        except Exception as e:
            logger.error(f"Failed to query GraphRAG: {e}", exc_info=True)
            raise
