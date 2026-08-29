"""Assessment management, retrieval, and persistence endpoints."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException

from app.core.logger import logger
from app.core.security import require_demo_key
from app.services.supabase_service import (
    AssessmentNotFoundError,
    SupabaseService,
    SupabaseServiceError,
)

router = APIRouter()


@router.get("", tags=["assessments"])
async def list_assessments() -> list[dict[str, Any]]:
    """List historical assessments stored in Supabase."""
    service = SupabaseService()
    if not service.is_available:
        return []
    try:
        return service.list_all_assessments()
    except Exception as exc:
        logger.error(f"Error listing assessments: {exc}")
        raise HTTPException(status_code=500, detail="Unable to retrieve assessments.")


@router.get("/{assessment_id}", tags=["assessments"])
async def get_assessment(assessment_id: str) -> dict[str, Any]:
    """Retrieve a persisted assessment session, mapped questions, and signed document URL."""
    service = SupabaseService()
    if not service.is_available:
        raise HTTPException(status_code=503, detail="Database persistence is not configured.")

    try:
        return service.fetch_assessment(assessment_id)
    except AssessmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SupabaseServiceError as exc:
        logger.error(f"Persistence error fetching assessment {assessment_id}: {exc}")
        raise HTTPException(status_code=503, detail="The persistence layer is unavailable.") from exc
    except Exception as exc:
        logger.error(f"Error fetching assessment {assessment_id}: {exc}")
        raise HTTPException(status_code=500, detail="Unable to retrieve assessment.") from exc


@router.delete("/{assessment_id}", tags=["assessments"], dependencies=[Depends(require_demo_key)])
async def delete_assessment(assessment_id: str) -> dict[str, bool]:
    """Delete a persisted assessment and its mapped questions."""
    service = SupabaseService()
    if not service.is_available:
        raise HTTPException(status_code=503, detail="Database persistence is not configured.")

    try:
        service.delete_assessment(assessment_id)
        return {"success": True}
    except AssessmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Error deleting assessment {assessment_id}: {exc}")
        raise HTTPException(status_code=500, detail="Unable to delete assessment.") from exc
