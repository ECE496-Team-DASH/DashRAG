"""
API Routes for Project Prometheus
Handles HTTP endpoints and request routing
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any


app = FastAPI(title="Project Prometheus API", version="1.0.0")


class QueryRequest(BaseModel):
    """Request model for RAG queries"""
    query: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    """Response model for RAG queries"""
    response: str
    session_id: str
    sources: Optional[list] = None


class APIRoutes:
    """Main API routes handler"""

    def __init__(self, rag_engine, session_manager):
        """
        Initialize API routes with dependencies

        Args:
            rag_engine: Instance of DashRAGEngine
            session_manager: Instance of SessionManager
        """
        self.rag_engine = rag_engine
        self.session_manager = session_manager

    def setup_routes(self):
        """Register all API routes"""

        @app.get("/")
        async def root():
            """Health check endpoint"""
            return {"status": "healthy", "service": "Project Prometheus API"}

        @app.post("/query", response_model=QueryResponse)
        async def process_query(request: QueryRequest):
            """
            Process a RAG query

            Args:
                request: QueryRequest with query text and optional session info

            Returns:
                QueryResponse with generated response and sources
            """
            try:
                # Get or create session
                session_id = request.session_id or self.session_manager.create_session()

                # Process query through RAG engine
                result = self.rag_engine.query(
                    query=request.query,
                    session_id=session_id,
                    context=request.context
                )

                return QueryResponse(
                    response=result["response"],
                    session_id=session_id,
                    sources=result.get("sources")
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @app.get("/session/{session_id}")
        async def get_session(session_id: str):
            """Get session information"""
            session = self.session_manager.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            return session


def create_app(rag_engine, session_manager):
    """
    Factory function to create and configure the FastAPI app

    Args:
        rag_engine: DashRAGEngine instance
        session_manager: SessionManager instance

    Returns:
        Configured FastAPI app
    """
    routes = APIRoutes(rag_engine, session_manager)
    routes.setup_routes()
    return app
