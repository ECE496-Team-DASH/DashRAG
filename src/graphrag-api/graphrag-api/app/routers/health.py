
from fastapi import APIRouter
from ..config import settings
from pathlib import Path
import shutil

router = APIRouter(tags=["health"])

@router.get(
    "/healthz",
    summary="Health check endpoint",
    description="""
    Check if the API is running and operational.
    
    **Checks performed:**
    - API is responding
    - Data directory is accessible
    - Data directory is writable
    - Available disk space
    
    **Use cases:**
    - Container orchestration health probes
    - Monitoring systems
    - Load balancer health checks
    - Pre-deployment validation
    
    **Returns:** System status information
    """,
    responses={
        200: {
            "description": "API is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "ok": True,
                        "data_root": "/app/data",
                        "can_write_data_root": True,
                        "free_space_mb": 15360
                    }
                }
            }
        }
    }
)
def healthz():
    """Health check - verify API and filesystem are operational"""
    can_write = False
    try:
        p = settings.data_root / ".healthz.tmp"
        p.write_text("ok", encoding="utf-8")
        can_write = p.exists()
        p.unlink(missing_ok=True)
    except Exception:
        can_write = False
    return {
        "ok": True,
        "data_root": str(settings.data_root),
        "can_write_data_root": can_write,
        "free_space_mb": shutil.disk_usage(settings.data_root).free // (1024*1024)
    }
