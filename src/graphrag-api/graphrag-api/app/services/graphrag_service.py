
from pathlib import Path
from typing import Optional, List
import os
import logging

from nano_graphrag import GraphRAG, QueryParam
from ..config import settings

logger = logging.getLogger(__name__)

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
        
        try:
            self.rag = GraphRAG(
                working_dir=str(self.working_dir),
                always_create_working_dir=True,
                enable_llm_cache=True,
                **provider_kwargs
            )
            logger.info("GraphRAG initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GraphRAG: {e}", exc_info=True)
            raise

    def insert_texts(self, texts: List[str] | str) -> None:
        """Insert text(s) into the knowledge graph"""
        logger.info(f"Inserting {'single document' if isinstance(texts, str) else f'{len(texts)} documents'} into GraphRAG")
        try:
            self.rag.insert(texts)
            logger.info("Text insertion completed successfully")
        except Exception as e:
            logger.error(f"Failed to insert texts into GraphRAG: {e}", exc_info=True)
            raise

    def query(self, prompt: str, **qp_kwargs) -> str:
        """Query the knowledge graph"""
        qp = QueryParam(**{k:v for k,v in qp_kwargs.items() if v is not None})
        logger.info(f"Querying GraphRAG with mode: {qp.mode}")
        try:
            result = self.rag.query(prompt, qp)
            logger.info("Query completed successfully")
            return result
        except Exception as e:
            logger.error(f"Failed to query GraphRAG: {e}", exc_info=True)
            raise
