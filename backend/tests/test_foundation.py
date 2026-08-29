import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import BoundingBox, Evaluation, QuestionItem, app


def test_health_is_available_without_external_keys() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_bounding_box_requires_a_nonzero_area() -> None:
    with pytest.raises(ValidationError, match="ymin < ymax"):
        BoundingBox(ymin=700, xmin=100, ymax=200, xmax=900)


def test_unanswered_question_cannot_contain_a_mapped_answer() -> None:
    with pytest.raises(ValidationError, match="Unanswered questions"):
        QuestionItem(
            id="q1",
            number="1",
            full_label="1",
            text="Define inertia.",
            max_marks=2,
            status="unanswered",
            transcribed_answer="An answer should not be present.",
            evaluation=Evaluation(score=0, max_marks=2, is_correct=False, feedback="No answer."),
        )
