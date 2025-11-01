
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

    async def query(self, prompt: str, **qp_kwargs) -> str:
        """Query the knowledge graph"""
        qp = QueryParam(**{k:v for k,v in qp_kwargs.items() if v is not None})
        logger.info(f"Querying GraphRAG with mode: {qp.mode}")
        try:
            result = await self.rag.aquery(prompt, qp)
            logger.info("Query completed successfully")
            return result
        except AssertionError as e:
            # Handle JSON parsing errors from LLM responses
            error_msg = str(e)
            if "Unable to parse JSON from response" in error_msg:
                # Extract the actual LLM response from the error message
                if "response: " in error_msg:
                    llm_response = error_msg.split("response: ", 1)[1]
                    logger.warning(f"LLM returned non-JSON response, using it directly: {llm_response[:100]}...")
                    return llm_response
                else:
                    logger.error(f"Could not extract LLM response from error: {error_msg}")
                    raise ValueError("The AI model returned an invalid response format. Please try again or rephrase your question.")
            else:
                # Re-raise if it's a different assertion error
                raise
        except Exception as e:
            logger.error(f"Failed to query GraphRAG: {e}", exc_info=True)
            raise
