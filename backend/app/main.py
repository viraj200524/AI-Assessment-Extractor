"""FastAPI Application entry point for VedaAI Assessment Extractor."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.schemas.assessment import AssessmentResponse
from app.schemas.question import (
    AnswerRegion,
    BoundingBox,
    Evaluation,
    QuestionItem,
    UnmatchedAnswer,
)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI Assessment Extraction, Answer Mapping, and Evaluation API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin).rstrip("/") for origin in settings.backend_cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)

# Direct exports for backwards compatibility
__all__ = [
    "app",
    "settings",
    "get_settings",
    "BoundingBox",
    "AnswerRegion",
    "Evaluation",
    "QuestionItem",
    "UnmatchedAnswer",
    "AssessmentResponse",
]
