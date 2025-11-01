
import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import Base, engine
from .routers import sessions, documents, messages, papers, health
from .config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Set specific loggers
logging.getLogger("app").setLevel(logging.INFO)
logging.getLogger("nano_graphrag").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # Reduce noise from access logs

logger = logging.getLogger(__name__)
logger.info(f"Starting DashRAG API with log level: {settings.log_level}")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="DashRAG Chat API",
    description="""
## GraphRAG-Powered Research Assistant API

Build session-based knowledge graphs from PDFs and arXiv papers, then query them with AI.

### Key Features
- 🗂️ **Session-based**: Each chat session has its own isolated knowledge graph
- 📄 **PDF Ingestion**: Upload PDFs or fetch from arXiv automatically
- 🤖 **AI Queries**: Local, global, or naive query modes via nano-graphrag
- 📊 **Knowledge Graphs**: Automatic entity/relationship extraction
- 💬 **Streaming**: Real-time SSE streaming for chat responses

### Typical Workflow
1. **Create a session** (`POST /sessions`)
2. **Add documents** (upload PDFs or fetch from arXiv)
3. **Query the knowledge graph** (`POST /sessions/{sid}/messages`)
4. **Export your research** (`GET /sessions/{sid}/export`)

### Query Modes
- **`local`**: Search specific text chunks (fast, precise)
- **`global`**: Cross-document synthesis via community detection (comprehensive)
- **`naive`**: Simple keyword matching (fastest)

### Authentication
Currently open (no auth). Add your own auth middleware for production.
    """,
    version="1.0.0",
    contact={
        "name": "DASH Team",
        "url": "https://github.com/ECE496-Team-DASH/project-prometheus",
    },
    license_info={
        "name": "MIT",
    },
)

# Allow all origins in dev; restrict in prod
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(documents.router)
app.include_router(messages.router)
app.include_router(papers.router)
