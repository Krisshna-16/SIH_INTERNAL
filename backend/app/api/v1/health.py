from datetime import datetime, timezone
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def get_health():
    """Health check endpoint returning application status and environment metadata."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.ENV,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
