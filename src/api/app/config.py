from pathlib import Path

class Settings:
    # Simple hardcoded defaults for local development
    data_root: Path = Path("./data")
    log_level: str = "INFO"
    database_url: str = "sqlite:///./dashrag.db"
    
    max_upload_mb: int = 100
    arxiv_max_results: int = 10
    
    # Optional features - set to None by default
    ngr_use_gemini: bool | None = None
    ngr_use_azure_openai: bool | None = None

settings = Settings()
settings.data_root.mkdir(parents=True, exist_ok=True)