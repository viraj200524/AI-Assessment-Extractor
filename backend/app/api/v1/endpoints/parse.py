"""Document upload, parsing, spatial grounding, evaluation, and persistence endpoints."""

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.core.config import Settings, get_settings
from app.core.logger import logger
from app.core.rate_limit import limit_parse_requests
from app.core.security import require_demo_key
from app.schemas.assessment import AssessmentResponse
from app.schemas.job import JobStatus
from app.schemas.question import Evaluation, QuestionItem, UnmatchedAnswer
from app.services.gemini_service import GeminiAssessmentService, GeminiProcessingError
from app.services.job_store import job_store
from app.services.pdf_service import DocumentProcessingError, rasterize_document
from app.services.supabase_service import SupabaseService

router = APIRouter()

_SUPPORTED_DOCUMENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}

# Thread pool for asynchronous background parsing jobs
_job_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="vedai-parse")


@dataclass(frozen=True)
class PreparedDocument:
    """Document payload staged to a temporary disk path for processing."""

    path: Path
    data: bytes
    content_type: str
    filename: str


StageCallback = Callable[[str, str | None], None]


def _noop_stage(stage_key: str, detail: str | None = None) -> None:
    return None


async def _stage_upload(upload: UploadFile, directory: Path, settings: Settings) -> PreparedDocument:
    content_type = (upload.content_type or "").lower()
    if content_type not in _SUPPORTED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Only PDF, PNG, and JPEG documents are supported.",
        )
    document_bytes = await upload.read()
    if not document_bytes:
        raise HTTPException(status_code=422, detail=f"{upload.filename or 'Upload'} is empty.")
    if len(document_bytes) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="A document exceeds the 50 MB upload limit.")

    extension = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}[content_type]
    destination = directory / f"{uuid4()}{extension}"
    destination.write_bytes(document_bytes)
    return PreparedDocument(
        path=destination,
        data=document_bytes,
        content_type=content_type,
        filename=upload.filename or f"document{extension}",
    )


def run_assessment_pipeline(
    question_paper: PreparedDocument,
    answer_sheet: PreparedDocument,
    workspace: Path,
    settings: Settings,
    assessment_id: str,
    on_stage: StageCallback = _noop_stage,
) -> tuple[AssessmentResponse, bool]:
    """Execute document rasterization, question extraction, answer mapping, and persistence."""
    on_stage("rasterizing", "Rendering question paper")
    question_pages = rasterize_document(
        question_paper.path,
        workspace / "question-pages",
        progress=lambda page, total: on_stage("rasterizing", f"Question paper page {page} of {total}"),
    )
    answer_pages = rasterize_document(
        answer_sheet.path,
        workspace / "answer-pages",
        progress=lambda page, total: on_stage("rasterizing", f"Answer sheet page {page} of {total}"),
    )

    gemini = GeminiAssessmentService()

    on_stage("parsing_questions", f"Reading {len(question_pages)} question paper page(s)")
    extracted_questions = gemini.extract_questions(question_pages)

    on_stage(
        "grounding_answers",
        f"Mapping {len(extracted_questions.questions)} question(s) across {len(answer_pages)} page(s)",
    )
    mapped_answers = gemini.map_answers(extracted_questions, answer_pages)

    mapping_by_id = {item.question_id: item for item in mapped_answers.mapped_answers}
    questions: list[QuestionItem] = []

    for extracted in extracted_questions.questions:
        mapping = mapping_by_id.get(extracted.id)
        if not mapping:
            mapping_status = "unanswered"
            mapping_transcribed = None
            mapping_regions = []
            score = 0.0
            is_correct = False
            feedback = "Question was not answered."
        else:
            mapping_status = mapping.status
            mapping_transcribed = mapping.transcribed_answer
            mapping_regions = mapping.answer_regions
            score = min(mapping.score, extracted.max_marks)
            is_correct = mapping.is_correct
            feedback = mapping.feedback or ("Correct" if is_correct else "Needs improvement.")

        questions.append(
            QuestionItem(
                id=extracted.id,
                number=extracted.number,
                subpart=extracted.subpart,
                full_label=extracted.full_label,
                text=extracted.text,
                max_marks=extracted.max_marks,
                status=mapping_status,
                transcribed_answer=mapping_transcribed,
                answer_regions=mapping_regions,
                evaluation=Evaluation(
                    score=score,
                    max_marks=extracted.max_marks,
                    is_correct=is_correct,
                    feedback=feedback,
                ),
            )
        )

    total_score = round(sum(q.evaluation.score for q in questions), 2)
    max_possible_score = round(sum(q.max_marks for q in questions), 2)
    percentage = round((total_score / max_possible_score * 100) if max_possible_score > 0 else 0.0, 2)

    on_stage("persisting", "Storing documents and results")
    persisted = _persist_assessment(
        settings=settings,
        assessment_id=assessment_id,
        question_paper=question_paper,
        answer_sheet=answer_sheet,
        answer_page_count=len(answer_pages),
        total_score=total_score,
        max_possible_score=max_possible_score,
        percentage=percentage,
        questions=questions,
        unmatched_answers=mapped_answers.unmatched_answers,
    )

    response = AssessmentResponse(
        assessment_id=assessment_id,
        total_score=total_score,
        max_possible_score=max_possible_score,
        percentage=percentage,
        questions=questions,
        unmatched_answers=mapped_answers.unmatched_answers,
    )
    return response, persisted


def _persist_assessment(
    *,
    settings: Settings,
    assessment_id: str,
    question_paper: PreparedDocument,
    answer_sheet: PreparedDocument,
    answer_page_count: int,
    total_score: float,
    max_possible_score: float,
    percentage: float,
    questions: list[QuestionItem],
    unmatched_answers: list[UnmatchedAnswer],
) -> bool:
    """Best-effort persistence. Returns whether the record reached Supabase."""
    supabase_service = SupabaseService()
    if not supabase_service.is_available:
        return False
    try:
        qp_storage_path = supabase_service.upload_document(
            bucket=settings.supabase_question_papers_bucket,
            file_name=question_paper.filename,
            data=question_paper.data,
            content_type=question_paper.content_type,
        )
        ans_storage_path = supabase_service.upload_document(
            bucket=settings.supabase_answer_sheets_bucket,
            file_name=answer_sheet.filename,
            data=answer_sheet.data,
            content_type=answer_sheet.content_type,
        )
        title = Path(question_paper.filename).stem.replace("_", " ").title()
        supabase_service.save_assessment_record(
            assessment_id=assessment_id,
            title=title,
            question_paper_path=qp_storage_path,
            answer_sheet_path=ans_storage_path,
            page_count=answer_page_count,
            total_score=total_score,
            max_score=max_possible_score,
            percentage=percentage,
            questions=questions,
            unmatched_answers=unmatched_answers,
        )
        return True
    except Exception as exc:
        logger.warning(f"Persistence to Supabase skipped due to error: {exc}")
        return False


def _http_error_for(exc: Exception) -> HTTPException:
    """Map pipeline exceptions to appropriate HTTP error status codes."""
    if isinstance(exc, DocumentProcessingError):
        return HTTPException(status_code=422, detail=str(exc))
    if isinstance(exc, GeminiProcessingError):
        return HTTPException(status_code=exc.status_code, detail=exc.detail)
    return HTTPException(status_code=500, detail="An unexpected error occurred while processing the assessment.")


@router.post(
    "/parse",
    response_model=AssessmentResponse,
    tags=["parsing"],
    dependencies=[Depends(require_demo_key), Depends(limit_parse_requests)],
)
async def parse_assessment(
    question_paper: UploadFile = File(..., description="Printed question paper: PDF, PNG, or JPEG."),
    answer_sheet: UploadFile = File(..., description="Handwritten answer sheet: PDF, PNG, or JPEG."),
    current_settings: Settings = Depends(get_settings),
) -> AssessmentResponse:
    """Run the assessment extraction pipeline synchronously."""
    try:
        with TemporaryDirectory(prefix="vedai-parse-") as temporary_directory:
            workspace = Path(temporary_directory)
            prepared_question_paper = await _stage_upload(question_paper, workspace, current_settings)
            prepared_answer_sheet = await _stage_upload(answer_sheet, workspace, current_settings)
            assessment_id = str(uuid4())

            try:
                # Offload blocking pipeline execution to worker thread
                response, _ = await asyncio.to_thread(
                    run_assessment_pipeline,
                    prepared_question_paper,
                    prepared_answer_sheet,
                    workspace,
                    current_settings,
                    assessment_id,
                )
            except (DocumentProcessingError, GeminiProcessingError) as exc:
                logger.error(f"Assessment pipeline failed: {exc}")
                raise _http_error_for(exc) from exc

            return response
    finally:
        await question_paper.close()
        await answer_sheet.close()


def _run_parse_job(
    job_id: str,
    question_paper: PreparedDocument,
    answer_sheet: PreparedDocument,
    workspace_handle: TemporaryDirectory,
    settings: Settings,
) -> None:
    """Worker function for executing a background parsing job."""
    assessment_id = str(uuid4())
    try:
        job_store.set_stage(job_id, "uploading", "Documents received")
        response, persisted = run_assessment_pipeline(
            question_paper,
            answer_sheet,
            Path(workspace_handle.name),
            settings,
            assessment_id,
            on_stage=lambda stage_key, detail=None: job_store.set_stage(job_id, stage_key, detail),
        )
        job_store.succeed(job_id, response, persisted)
        if not persisted:
            logger.warning(f"Job {job_id} finished but its assessment was not persisted.")
    except (DocumentProcessingError, GeminiProcessingError) as exc:
        error = _http_error_for(exc)
        logger.error(f"Job {job_id} failed: {exc}")
        job_store.fail(job_id, str(error.detail), error.status_code)
    except Exception:
        logger.exception(f"Job {job_id} failed unexpectedly")
        job_store.fail(job_id, "An unexpected error occurred while processing the assessment.", 500)
    finally:
        workspace_handle.cleanup()


@router.post(
    "/parse/jobs",
    response_model=JobStatus,
    status_code=202,
    tags=["parsing"],
    dependencies=[Depends(require_demo_key), Depends(limit_parse_requests)],
)
async def create_parse_job(
    question_paper: UploadFile = File(..., description="Printed question paper: PDF, PNG, or JPEG."),
    answer_sheet: UploadFile = File(..., description="Handwritten answer sheet: PDF, PNG, or JPEG."),
    current_settings: Settings = Depends(get_settings),
) -> JobStatus:
    """Create a background parsing job and return its initial status."""
    workspace_handle = TemporaryDirectory(prefix="vedai-job-")
    try:
        workspace = Path(workspace_handle.name)
        prepared_question_paper = await _stage_upload(question_paper, workspace, current_settings)
        prepared_answer_sheet = await _stage_upload(answer_sheet, workspace, current_settings)
    except BaseException:
        workspace_handle.cleanup()
        raise
    finally:
        await question_paper.close()
        await answer_sheet.close()

    job = job_store.create()
    _job_executor.submit(
        _run_parse_job,
        job.job_id,
        prepared_question_paper,
        prepared_answer_sheet,
        workspace_handle,
        current_settings,
    )
    logger.info(f"Queued parsing job {job.job_id}")
    return job.to_status()


@router.get("/parse/jobs/{job_id}", response_model=JobStatus, tags=["parsing"])
async def get_parse_job(job_id: str) -> JobStatus:
    """Poll the status of an ongoing parsing job."""
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown or expired parsing job.")
    return job.to_status()


@router.get("/parse/jobs/{job_id}/result", response_model=AssessmentResponse, tags=["parsing"])
async def get_parse_job_result(job_id: str) -> AssessmentResponse:
    """Retrieve the finished assessment result for a completed parsing job."""
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown or expired parsing job.")
    if job.state == "failed":
        raise HTTPException(status_code=job.error_status or 502, detail=job.error or "Processing failed.")
    if job.state != "succeeded" or job.result is None:
        raise HTTPException(status_code=409, detail="This assessment is still being processed.")
    return job.result


def _sse(payload: dict[str, Any], event: str = "status") -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


@router.get("/parse/jobs/{job_id}/events", tags=["parsing"])
async def stream_parse_job(job_id: str, request: Request) -> StreamingResponse:
    """Stream parsing progress updates using Server-Sent Events."""
    if job_store.get(job_id) is None:
        raise HTTPException(status_code=404, detail="Unknown or expired parsing job.")

    poll_interval = 0.3
    keepalive_after = 15.0

    async def event_stream() -> AsyncIterator[str]:
        last_version = -1
        idle_seconds = 0.0
        while True:
            if await request.is_disconnected():
                logger.info(f"Client disconnected from job {job_id} event stream.")
                break

            job = job_store.get(job_id)
            if job is None:
                yield _sse({"job_id": job_id, "error": "This job has expired."}, event="expired")
                break

            if job.version != last_version:
                last_version = job.version
                idle_seconds = 0.0
                yield _sse(job.to_status().model_dump(mode="json"))
                if job.state in ("succeeded", "failed"):
                    break
            else:
                idle_seconds += poll_interval
                if idle_seconds >= keepalive_after:
                    idle_seconds = 0.0
                    # Send periodic keepalive comment frame to maintain connection
                    yield ": keepalive\n\n"

            await asyncio.sleep(poll_interval)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
