"""Health and system liveness endpoint."""

from fastapi import APIRouter, Depends
from app.core.config import Settings, get_settings

router = APIRouter()


@router.get("/health", tags=["health"])
def health_check(current_settings: Settings = Depends(get_settings)) -> dict[str, str | bool]:
    """Liveness endpoint which never returns secret values."""
    return {
        "status": "ok",
        "environment": current_settings.app_env,
        "supabase_configured": current_settings.supabase_is_configured,
        "gemini_configured": current_settings.gemini_is_configured,
        # Whether writes need a shared key. Reveals only that a key is configured, never
        # its value, so the client can decide whether to show the access-key field.
        "access_key_required": current_settings.demo_access_key_required,
    }
