from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file (override any existing values)
load_dotenv(override=True)

class Settings:
    # Simple hardcoded defaults for local development
    data_root: Path = Path(os.getenv("DATA_ROOT", "./data"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./dashrag.db")
    
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "100"))
    arxiv_max_results: int = int(os.getenv("ARXIV_MAX_RESULTS", "10"))
    
    # Auth settings
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    
    # CORS allowed origins (comma-separated). Defaults include localhost dev + Vercel deployment.
    cors_origins: list[str] = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,https://dashrag.vercel.app").split(",")
        if o.strip()
    ]

    # Maximum seconds a GraphRAG query may run before being cancelled.
    query_timeout_seconds: int = int(os.getenv("QUERY_TIMEOUT_SECONDS", "180"))

    # Optional features - set to None by default
    ngr_use_gemini: bool | None = None
    ngr_use_azure_openai: bool | None = None
    
    # API Keys (these will be available as environment variables for nano-graphrag)
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")

settings = Settings()
settings.data_root.mkdir(parents=True, exist_ok=True)

# Ensure API keys are set in environment for nano-graphrag to find
if settings.gemini_api_key:
    os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
if settings.openai_api_key:
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key
if settings.azure_openai_api_key:
    os.environ["AZURE_OPENAI_API_KEY"] = settings.azure_openai_api_key
if settings.azure_openai_endpoint:
    os.environ["AZURE_OPENAI_ENDPOINT"] = settings.azure_openai_endpoint