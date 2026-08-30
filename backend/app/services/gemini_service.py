"""Google Gemini multimodal AI service for assessment extraction, spatial grounding, and evaluation."""

import json
from collections.abc import Sequence
from typing import Any, Callable

import httpx
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.logger import logger
from app.schemas.gemini import (
    AnswerSheetExtraction,
    MappedAnswer,
    QuestionPaperExtraction,
)
from app.services.pdf_service import RasterizedPage


class GeminiProcessingError(RuntimeError):
    """Base exception for Gemini API processing errors."""

    status_code = 502
    default_detail = "The AI extraction service returned an unusable result."

    def __init__(self, detail: str | None = None, *, upstream: str | None = None) -> None:
        self.detail = detail or self.default_detail
        self.upstream = upstream
        super().__init__(f"{self.detail} (upstream: {upstream})" if upstream else self.detail)


class GeminiConfigurationError(GeminiProcessingError):
    status_code = 500
    default_detail = "GEMINI_API_KEY is not configured on the server."


class GeminiAuthError(GeminiProcessingError):
    status_code = 500
    default_detail = "The configured Gemini API key was rejected. Check GEMINI_API_KEY."


class GeminiQuotaError(GeminiProcessingError):
    status_code = 429
    default_detail = "The Gemini API quota or rate limit is exhausted. Please retry shortly."


class GeminiTimeoutError(GeminiProcessingError):
    status_code = 504
    default_detail = (
        "Gemini did not respond in time. Retry, or split the document into fewer pages."
    )


class GeminiUnavailableError(GeminiProcessingError):
    status_code = 503
    default_detail = "The Gemini API is temporarily unavailable. Please retry shortly."


class GeminiInvalidDocumentError(GeminiProcessingError):
    status_code = 422
    default_detail = (
        "Gemini could not read one of the uploaded pages. Re-export the document and try again."
    )


class GeminiResponseError(GeminiProcessingError):
    status_code = 502
    default_detail = "Gemini returned a response that could not be interpreted."


def _classify_api_error(exc: Exception, model: str) -> GeminiProcessingError:
    """Classify SDK and transport exceptions into typed errors."""
    if isinstance(exc, APIError):
        code = getattr(exc, "code", None)
        status = (getattr(exc, "status", None) or "").upper()
        message = getattr(exc, "message", None) or str(exc)
        upstream = f"{code} {status}: {message}".strip()

        if code in (401, 403) or status in {"UNAUTHENTICATED", "PERMISSION_DENIED"}:
            return GeminiAuthError(upstream=upstream)
        if code == 429 or status == "RESOURCE_EXHAUSTED":
            return GeminiQuotaError(upstream=upstream)
        if code == 404 or status == "NOT_FOUND":
            return GeminiConfigurationError(
                f"Gemini model '{model}' was not found or is not available to this API key. "
                "Check GEMINI_MODEL.",
                upstream=upstream,
            )
        if code == 400 or status == "INVALID_ARGUMENT":
            return GeminiInvalidDocumentError(upstream=upstream)
        if code == 504 or status == "DEADLINE_EXCEEDED":
            return GeminiTimeoutError(upstream=upstream)
        if isinstance(code, int) and code >= 500:
            return GeminiUnavailableError(upstream=upstream)
        return GeminiResponseError(upstream=upstream)

    if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
        return GeminiTimeoutError(upstream=f"{type(exc).__name__}: {exc}")
    if isinstance(exc, (httpx.TransportError, ConnectionError, OSError)):
        return GeminiUnavailableError(
            "Could not reach the Gemini API. Check network connectivity.",
            upstream=f"{type(exc).__name__}: {exc}",
        )
    return GeminiResponseError(upstream=f"{type(exc).__name__}: {exc}")


QUESTION_PAPER_PROMPT = """You are extracting a printed examination question paper.
Read every supplied page in natural printed order. Return every assessable question in exactly that order.
Split every labelled subpart into a separate question (for example 11(a) and 11(b)). Preserve the printed
label in full_label, assign a stable id such as q11_a, extract its wording, and extract its maximum marks.
Use 0 for max_marks only when no mark allocation is visible. Never invent questions, reorder questions,
or combine labelled subparts. Return only the requested structured result."""


ANSWER_MAPPING_PROMPT = """You are an expert examiner mapping, spatially grounding, and evaluating a student's handwritten answer sheet against an extracted question list.
Use the question JSON supplied below as the authoritative target list. Inspect all answer-sheet page images thoroughly.

For EVERY question in the target question list:
1. Map the student's answer:
   - status: "answered" if written in expected sequence, "out_of_order" if written elsewhere or mislabelled, or "unanswered" if no answer exists.
   - transcribed_answer: Transcribe the complete multi-line handwritten answer text faithfully, line-by-line. If unanswered, leave null.

2. SPATIAL BOUNDING BOX GROUNDING (`answer_regions.box_2d`):
   - For every answered or out_of_order question, provide one or more normalized 2D bounding boxes (ymin, xmin, ymax, xmax on a scale of 0 to 1000) with 1-indexed page_number.
   - Fit each box tightly to the ink actually written for that answer. Do not pad it out to the page margins, and do not use a fixed width: a one-word answer gets a small box, a full paragraph gets a wide one.
   - ymin: at or just above the question label and the first line of the answer.
   - ymax: below the VERY LAST line, bullet, formula, or concluding sentence of this answer block. Never stop after the first 1-2 lines of a multi-line answer.
   - xmin / xmax: the left and right edges of the written content, from the question label to the end of the longest line in the block.
   - Multi-page responses: If an answer spans across page boundaries, output a separate AnswerRegion for each page covering that page's portion.

3. Evaluate and grade the response:
   - score: Fair marks awarded from 0.0 up to the question's max_marks based on correctness, completeness, and clarity. If unanswered, score must be 0.0.
   - is_correct: True if substantially correct / full marks, False if incorrect, severely incomplete, or unanswered.
   - feedback: A concise, constructive explanation of why marks were awarded or deducted. If unanswered, use "Question was not answered."

4. Extraneous writing:
   - Place any unrelated writing, scratchwork, or unmapped notes in unmatched_answers with its own bounding box, transcription, and reason.

Return only the requested structured result."""


# Normalization helpers: clean and sanitize raw model outputs before Pydantic validation
_MAX_COORD = 1000
_VALID_STATUSES = {"answered", "unanswered", "out_of_order"}


def _clean_str(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _repair_box(raw: Any) -> dict[str, int] | None:
    """Clamp raw box coordinates into [0, 1000]. Returns None if degenerate or invalid."""
    if not isinstance(raw, dict):
        return None
    box: dict[str, int] = {}
    for key in ("ymin", "xmin", "ymax", "xmax"):
        try:
            box[key] = max(0, min(_MAX_COORD, int(round(float(raw[key])))))
        except (KeyError, TypeError, ValueError):
            return None
    if box["ymin"] >= box["ymax"] or box["xmin"] >= box["xmax"]:
        return None
    return box


def _repair_regions(raw: Any, *, context: str) -> list[dict[str, Any]]:
    regions: list[dict[str, Any]] = []
    dropped = 0
    for item in raw if isinstance(raw, list) else []:
        box = _repair_box(item.get("box_2d") if isinstance(item, dict) else None)
        try:
            page_number = int(item["page_number"])  # type: ignore[index]
        except (KeyError, TypeError, ValueError):
            page_number = 0
        if box is None or page_number < 1:
            dropped += 1
            continue
        regions.append({"page_number": page_number, "box_2d": box})
    if dropped:
        logger.warning(f"Dropped {dropped} unusable answer region(s) for {context}.")
    return regions


def _repair_mapped_answer(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    question_id = _clean_str(raw.get("question_id"))
    if not question_id:
        return None

    transcribed = _clean_str(raw.get("transcribed_answer")) or None
    status = raw.get("status")
    if status not in _VALID_STATUSES:
        status = "answered" if transcribed else "unanswered"

    regions = _repair_regions(raw.get("answer_regions"), context=f"question {question_id}")
    try:
        score = max(0.0, float(raw.get("score") or 0.0))
    except (TypeError, ValueError):
        score = 0.0
    is_correct = bool(raw.get("is_correct"))
    feedback = _clean_str(raw.get("feedback"))

    if status == "unanswered":
        transcribed, regions, score, is_correct = None, [], 0.0, False
        feedback = feedback or "Question was not answered."
    else:
        feedback = feedback or "The evaluator did not return feedback for this answer."
        if not regions:
            logger.warning(
                f"Question {question_id} is {status} but has no usable answer region; "
                "it will be listed without a document highlight."
            )

    return {
        "question_id": question_id,
        "status": status,
        "transcribed_answer": transcribed,
        "answer_regions": regions,
        "score": score,
        "is_correct": is_correct,
        "feedback": feedback,
    }


def _repair_unmatched_answer(raw: Any, index: int) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    text = _clean_str(raw.get("transcribed_text"))
    box = _repair_box(raw.get("box_2d"))
    try:
        page_number = int(raw["page_number"])
    except (KeyError, TypeError, ValueError):
        page_number = 0
    if not text or box is None or page_number < 1:
        return None
    return {
        "id": _clean_str(raw.get("id")) or f"unmatched_{index + 1}",
        "page_number": page_number,
        "box_2d": box,
        "transcribed_text": text,
        "reason": _clean_str(raw.get("reason")) or "Unmapped student writing.",
    }


def _repair_question(raw: Any, seen_ids: set[str]) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    text = _clean_str(raw.get("text"))
    full_label = _clean_str(raw.get("full_label"))
    number = _clean_str(raw.get("number")) or full_label
    if not text or not (full_label or number):
        return None
    full_label = full_label or number

    identifier = _clean_str(raw.get("id")) or f"q{full_label}"
    if identifier in seen_ids:
        suffix = 2
        while f"{identifier}_{suffix}" in seen_ids:
            suffix += 1
        logger.warning(f"Duplicate question id '{identifier}' renamed to '{identifier}_{suffix}'.")
        identifier = f"{identifier}_{suffix}"
    seen_ids.add(identifier)

    try:
        max_marks = max(0.0, float(raw.get("max_marks") or 0.0))
    except (TypeError, ValueError):
        max_marks = 0.0

    subpart = _clean_str(raw.get("subpart")) or None
    return {
        "id": identifier,
        "number": number or full_label,
        "subpart": subpart,
        "full_label": full_label,
        "text": text,
        "max_marks": max_marks,
    }


def repair_question_paper_payload(payload: Any) -> dict[str, Any]:
    raw_questions = payload.get("questions") if isinstance(payload, dict) else None
    seen_ids: set[str] = set()
    questions: list[dict[str, Any]] = []
    dropped = 0
    for item in raw_questions if isinstance(raw_questions, list) else []:
        repaired = _repair_question(item, seen_ids)
        if repaired is None:
            dropped += 1
        else:
            questions.append(repaired)
    if dropped:
        logger.warning(f"Dropped {dropped} unreadable question entr(ies) from the question paper.")
    return {"questions": questions}


def repair_answer_sheet_payload(payload: Any) -> dict[str, Any]:
    raw = payload if isinstance(payload, dict) else {}

    mapped: list[dict[str, Any]] = []
    dropped_answers = 0
    raw_mapped = raw.get("mapped_answers")
    for item in raw_mapped if isinstance(raw_mapped, list) else []:
        repaired = _repair_mapped_answer(item)
        if repaired is None:
            dropped_answers += 1
        else:
            mapped.append(repaired)

    unmatched: list[dict[str, Any]] = []
    dropped_unmatched = 0
    raw_unmatched = raw.get("unmatched_answers")
    for index, item in enumerate(raw_unmatched if isinstance(raw_unmatched, list) else []):
        repaired = _repair_unmatched_answer(item, index)
        if repaired is None:
            dropped_unmatched += 1
        else:
            unmatched.append(repaired)

    if dropped_answers:
        logger.warning(f"Dropped {dropped_answers} unusable mapped answer(s); they fall back to unanswered.")
    if dropped_unmatched:
        logger.warning(f"Dropped {dropped_unmatched} unusable unmatched-answer entr(ies).")

    return {"mapped_answers": mapped, "unmatched_answers": unmatched}


class GeminiAssessmentService:
    def __init__(self, client: Any | None = None, model: str | None = None) -> None:
        settings = get_settings()
        if client is None:
            if not settings.gemini_api_key:
                raise GeminiConfigurationError()
            client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
        self._client = client
        self._model = model or settings.gemini_model

    def extract_questions(self, pages: Sequence[RasterizedPage]) -> QuestionPaperExtraction:
        logger.info(f"Extracting questions from {len(pages)} question paper pages...")
        return self._generate(
            QuestionPaperExtraction,
            QUESTION_PAPER_PROMPT,
            pages,
            repair=repair_question_paper_payload,
        )

    def map_answers(
        self,
        questions: QuestionPaperExtraction,
        pages: Sequence[RasterizedPage],
    ) -> AnswerSheetExtraction:
        logger.info(f"Mapping, grounding & grading answers across {len(pages)} answer sheet pages for {len(questions.questions)} questions...")
        context = json.dumps(questions.model_dump(mode="json"), ensure_ascii=False)
        mapping = self._generate(
            AnswerSheetExtraction,
            f"{ANSWER_MAPPING_PROMPT}\n\nTarget Questions:\n{context}",
            pages,
            repair=repair_answer_sheet_payload,
        )
        expected_questions = {q.id: q for q in questions.questions}
        expected_ids = set(expected_questions.keys())
        mapped_ids = [answer.question_id for answer in mapping.mapped_answers]
        unknown_ids = set(mapped_ids) - expected_ids
        if unknown_ids:
            logger.warning(f"Gemini mapped unknown question IDs: {sorted(unknown_ids)}")

        # Enforce max_marks bounds on evaluations
        for answer in mapping.mapped_answers:
            target_q = expected_questions.get(answer.question_id)
            if target_q and answer.score > target_q.max_marks:
                answer.score = target_q.max_marks

        # Ensure all expected questions have an entry
        mapped_dict = {a.question_id: a for a in mapping.mapped_answers if a.question_id in expected_ids}
        missing_ids = expected_ids - set(mapped_dict.keys())
        if missing_ids:
            for missing_id in sorted(missing_ids):
                mapping.mapped_answers.append(
                    MappedAnswer(
                        question_id=missing_id,
                        status="unanswered",
                        score=0.0,
                        is_correct=False,
                        feedback="Question was not answered.",
                    )
                )

        return mapping

    def _generate(
        self,
        result_type: type[BaseModel],
        prompt: str,
        pages: Sequence[RasterizedPage],
        *,
        repair: Callable[[Any], dict[str, Any]],
    ) -> Any:
        if not pages:
            raise GeminiInvalidDocumentError("At least one rasterized page is required.")
        parts: list[Any] = [prompt]
        parts.extend(
            types.Part.from_bytes(data=page.path.read_bytes(), mime_type="image/jpeg") for page in pages
        )

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=parts,
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                    response_json_schema=result_type.model_json_schema(),
                ),
            )
        except Exception as exc:
            error = _classify_api_error(exc, self._model)
            logger.error(f"Gemini call failed [{type(error).__name__}]: {error.upstream or error.detail}")
            raise error from exc

        text = (response.text or "").strip() if getattr(response, "text", None) else ""
        if not text:
            reason = _describe_empty_response(response)
            logger.error(f"Gemini returned an empty response. {reason}")
            raise GeminiResponseError(
                "Gemini returned an empty response, which usually means the request was "
                "blocked or truncated.",
                upstream=reason,
            )

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error(f"Gemini returned malformed JSON: {exc}")
            raise GeminiResponseError("Gemini returned malformed JSON.", upstream=str(exc)) from exc

        try:
            return result_type.model_validate(repair(payload))
        except ValidationError as exc:
            logger.error(f"Gemini payload failed validation after repair: {exc}")
            raise GeminiResponseError(
                "Gemini returned a response that did not match the expected structure.",
                upstream=str(exc),
            ) from exc


def _describe_empty_response(response: Any) -> str:
    """Extract whatever the SDK can tell us about why a response came back empty."""
    details: list[str] = []
    feedback = getattr(response, "prompt_feedback", None)
    blocked = getattr(feedback, "block_reason", None)
    if blocked:
        details.append(f"prompt blocked: {blocked}")
    for candidate in getattr(response, "candidates", None) or []:
        finish = getattr(candidate, "finish_reason", None)
        if finish:
            details.append(f"finish_reason: {finish}")
    return "; ".join(details) or "no candidate or block reason reported"
