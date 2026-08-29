"""A single imperfect item must cost one item, not the whole extraction (FR-06..FR-13).

Each payload here previously raised GeminiProcessingError and returned 502, discarding a
complete multi-call extraction because of one malformed field.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from google.genai.errors import ClientError, ServerError

from app.services.gemini_service import (
    GeminiAssessmentService,
    GeminiAuthError,
    GeminiConfigurationError,
    GeminiInvalidDocumentError,
    GeminiQuotaError,
    GeminiResponseError,
    GeminiTimeoutError,
    GeminiUnavailableError,
    _classify_api_error,
    repair_answer_sheet_payload,
    repair_question_paper_payload,
)
from app.services.pdf_service import RasterizedPage

QUESTION_PAPER = {
    "questions": [
        {"id": "q1", "number": "1", "full_label": "1", "text": "Define inertia.", "max_marks": 2},
        {"id": "q2", "number": "2", "full_label": "2", "text": "State Newton's law.", "max_marks": 3},
    ]
}

GOOD_BOX = {"ymin": 100, "xmin": 100, "ymax": 300, "xmax": 800}


class FakeModels:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = responses

    def generate_content(self, **_: object) -> SimpleNamespace:
        return SimpleNamespace(text=json.dumps(self.responses.pop(0)))


def _service(mapping_payload: dict) -> tuple[GeminiAssessmentService, RasterizedPage]:
    client = SimpleNamespace(models=FakeModels([QUESTION_PAPER, mapping_payload]))
    return GeminiAssessmentService(client=client, model="test-model")


def _run(mapping_payload: dict, tmp_path: Path):
    image = tmp_path / "page.jpg"
    image.write_bytes(b"test image bytes")
    service = _service(mapping_payload)
    page = RasterizedPage(page_number=1, path=image, width=100, height=100)
    return service.map_answers(service.extract_questions([page]), [page])


def test_answered_without_region_is_kept_not_fatal(tmp_path: Path) -> None:
    """The answer and its grade survive; only the highlight is unavailable."""
    result = _run(
        {
            "mapped_answers": [
                {
                    "question_id": "q1",
                    "status": "answered",
                    "transcribed_answer": "Resistance to change in motion.",
                    "answer_regions": [],
                    "score": 2.0,
                    "is_correct": True,
                    "feedback": "Correct.",
                }
            ],
            "unmatched_answers": [],
        },
        tmp_path,
    )
    answer = next(a for a in result.mapped_answers if a.question_id == "q1")
    assert answer.status == "answered"
    assert answer.score == 2.0
    assert answer.transcribed_answer == "Resistance to change in motion."
    assert answer.answer_regions == []


def test_blank_feedback_is_backfilled_not_fatal(tmp_path: Path) -> None:
    result = _run(
        {
            "mapped_answers": [
                {
                    "question_id": "q1",
                    "status": "answered",
                    "transcribed_answer": "A.",
                    "answer_regions": [{"page_number": 1, "box_2d": GOOD_BOX}],
                    "score": 2.0,
                    "is_correct": True,
                    "feedback": "",
                }
            ],
            "unmatched_answers": [],
        },
        tmp_path,
    )
    answer = next(a for a in result.mapped_answers if a.question_id == "q1")
    assert answer.feedback.strip()
    assert answer.score == 2.0


def test_degenerate_box_is_dropped_and_siblings_survive(tmp_path: Path) -> None:
    """A zero-height rectangle is discarded, never stretched into a fabricated region."""
    result = _run(
        {
            "mapped_answers": [
                {
                    "question_id": "q1",
                    "status": "answered",
                    "transcribed_answer": "A.",
                    "answer_regions": [
                        {"page_number": 1, "box_2d": {"ymin": 100, "xmin": 10, "ymax": 100, "xmax": 900}},
                        {"page_number": 2, "box_2d": GOOD_BOX},
                    ],
                    "score": 2.0,
                    "is_correct": True,
                    "feedback": "Good.",
                }
            ],
            "unmatched_answers": [],
        },
        tmp_path,
    )
    answer = next(a for a in result.mapped_answers if a.question_id == "q1")
    assert [region.page_number for region in answer.answer_regions] == [2]


def test_unmatched_answer_with_blank_reason_is_kept(tmp_path: Path) -> None:
    result = _run(
        {
            "mapped_answers": [
                {
                    "question_id": "q1",
                    "status": "answered",
                    "transcribed_answer": "A.",
                    "answer_regions": [{"page_number": 1, "box_2d": GOOD_BOX}],
                    "score": 2.0,
                    "is_correct": True,
                    "feedback": "Good.",
                }
            ],
            "unmatched_answers": [
                {
                    "id": "",
                    "page_number": 1,
                    "box_2d": GOOD_BOX,
                    "transcribed_text": "Rough work: 9.8 * 2",
                    "reason": "",
                }
            ],
        },
        tmp_path,
    )
    assert len(result.unmatched_answers) == 1
    assert result.unmatched_answers[0].id
    assert result.unmatched_answers[0].reason


def test_every_expected_question_still_gets_an_entry(tmp_path: Path) -> None:
    """FR-08: questions Gemini never mentioned are backfilled as unanswered."""
    result = _run({"mapped_answers": [], "unmatched_answers": []}, tmp_path)
    assert {a.question_id for a in result.mapped_answers} == {"q1", "q2"}
    assert all(a.status == "unanswered" and a.score == 0.0 for a in result.mapped_answers)


def test_duplicate_question_ids_are_renamed_not_rejected() -> None:
    repaired = repair_question_paper_payload(
        {
            "questions": [
                {"id": "q1", "number": "1", "full_label": "1", "text": "First.", "max_marks": 1},
                {"id": "q1", "number": "2", "full_label": "2", "text": "Second.", "max_marks": 1},
            ]
        }
    )
    assert [q["id"] for q in repaired["questions"]] == ["q1", "q1_2"]


def test_out_of_range_coordinates_are_clamped() -> None:
    repaired = repair_answer_sheet_payload(
        {
            "mapped_answers": [
                {
                    "question_id": "q1",
                    "status": "answered",
                    "transcribed_answer": "A.",
                    "answer_regions": [
                        {"page_number": 1, "box_2d": {"ymin": -40, "xmin": 10, "ymax": 4000, "xmax": 900}}
                    ],
                    "score": 1.0,
                    "is_correct": True,
                    "feedback": "ok",
                }
            ],
            "unmatched_answers": [],
        }
    )
    box = repaired["mapped_answers"][0]["answer_regions"][0]["box_2d"]
    assert box["ymin"] == 0 and box["ymax"] == 1000


@pytest.mark.parametrize(
    ("exception", "expected"),
    [
        (ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "quota"}}), GeminiQuotaError),
        (ClientError(403, {"error": {"code": 403, "status": "PERMISSION_DENIED", "message": "bad key"}}), GeminiAuthError),
        (ClientError(404, {"error": {"code": 404, "status": "NOT_FOUND", "message": "no model"}}), GeminiConfigurationError),
        (ClientError(400, {"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "bad image"}}), GeminiInvalidDocumentError),
        (ServerError(503, {"error": {"code": 503, "status": "UNAVAILABLE", "message": "overloaded"}}), GeminiUnavailableError),
        (httpx.ReadTimeout("timed out"), GeminiTimeoutError),
        (httpx.ConnectError("no route"), GeminiUnavailableError),
        (ValueError("something else"), GeminiResponseError),
    ],
)
def test_upstream_failures_are_classified_distinctly(exception: Exception, expected: type) -> None:
    """Every failure used to collapse into 'response failed validation'."""
    error = _classify_api_error(exception, "gemini-3.6-flash")
    assert isinstance(error, expected)
    assert error.detail != GeminiResponseError.default_detail or expected is GeminiResponseError


def test_classified_errors_carry_distinct_status_codes() -> None:
    assert GeminiQuotaError().status_code == 429
    assert GeminiTimeoutError().status_code == 504
    assert GeminiUnavailableError().status_code == 503
    assert GeminiInvalidDocumentError().status_code == 422
    assert GeminiAuthError().status_code == 500
    assert GeminiResponseError().status_code == 502
