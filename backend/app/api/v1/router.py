"""API v1 router assembly."""

from fastapi import APIRouter

from app.api.v1.endpoints import assessment, health, parse

api_router = APIRouter()

api_router.include_router(health.router, prefix="", tags=["health"])
api_router.include_router(parse.router, prefix="", tags=["parsing"])
api_router.include_router(assessment.router, prefix="/assessments", tags=["assessments"])
