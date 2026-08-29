"""Supabase client instantiation and database session management."""

from functools import lru_cache
from typing import Any

from app.core.config import get_settings
from app.core.logger import logger


@lru_cache
def get_supabase_client() -> Any:
    """Instantiate and cache the Supabase client using service role credentials."""
    settings = get_settings()
    if not settings.supabase_is_configured:
        logger.warning("Supabase credentials are not configured.")
        return None

    try:
        from supabase import Client, create_client

        client: Client = create_client(
            str(settings.supabase_url),
            settings.supabase_service_role_key.get_secret_value(),
        )
        return client
    except Exception as exc:
        logger.error(f"Failed to initialize Supabase client: {exc}")
        return None
