"""Dependency injection helpers for FastAPI endpoints."""

from typing import Any
from fastapi import Depends

from app.core.config import Settings, get_settings
from app.core.database import get_supabase_client


def get_current_settings() -> Settings:
    return get_settings()


def get_db(settings: Settings = Depends(get_current_settings)) -> Any:
    return get_supabase_client()
