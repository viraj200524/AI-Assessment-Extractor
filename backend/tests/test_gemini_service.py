import json
from pathlib import Path
from types import SimpleNamespace

from app.services.gemini_service import GeminiAssessmentService
from app.services.pdf_service import RasterizedPage


class FakeModels:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = responses

    def generate_content(self, **_: object) -> SimpleNamespace:
        return SimpleNamespace(text=json.dumps(self.responses.pop(0)))


def test_two_stage_pipeline_validates_and_normalizes_missing_questions(tmp_path: Path) -> None:
    image = tmp_path / "page.jpg"
    image.write_bytes(b"test image bytes")
    client = SimpleNamespace(
        models=FakeModels(
            [
                {
                    "questions": [
                        {"id": "q1", "number": "1", "full_label": "1", "text": "Define inertia.", "max_marks": 2},
                        {"id": "q2", "number": "2", "full_label": "2", "text": "State Newton's law.", "max_marks": 3},
                    ]
                },
                {
                    "mapped_answers": [
                        {
                            "question_id": "q1",
                            "status": "answered",
                            "transcribed_answer": "Resistance to change in motion.",
                            "answer_regions": [{"page_number": 1, "box_2d": {"ymin": 100, "xmin": 100, "ymax": 300, "xmax": 800}}],
                            "score": 2.0,
                            "is_correct": True,
                            "feedback": "Correct definition of inertia provided.",
                        }
                    ],
                    "unmatched_answers": [],
                },
            ]
        )
    )
    service = GeminiAssessmentService(client=client, model="test-model")
    page = RasterizedPage(page_number=1, path=image, width=100, height=100)

    questions = service.extract_questions([page])
    mapped = service.map_answers(questions, [page])

    assert [item.question_id for item in mapped.mapped_answers] == ["q1", "q2"]
    assert mapped.mapped_answers[0].score == 2.0
    assert mapped.mapped_answers[0].is_correct is True
    assert mapped.mapped_answers[1].status == "unanswered"
    assert mapped.mapped_answers[1].score == 0.0
    assert mapped.mapped_answers[1].is_correct is False


def test_model_bounding_boxes_are_passed_through_unmodified(tmp_path: Path) -> None:
    """Verify that tight bounding box coordinates from the model are preserved without inflation."""
    image = tmp_path / "page.jpg"
    image.write_bytes(b"test image bytes")

    tight_box = {"ymin": 201, "xmin": 147, "ymax": 222, "xmax": 206}
    client = SimpleNamespace(
        models=FakeModels(
            [
                {"questions": [{"id": "q1", "number": "1", "full_label": "1", "text": "Pick one.", "max_marks": 1}]},
                {
                    "mapped_answers": [
                        {
                            "question_id": "q1",
                            "status": "answered",
                            "transcribed_answer": "1. C",
                            "answer_regions": [{"page_number": 1, "box_2d": tight_box}],
                            "score": 1.0,
                            "is_correct": True,
                            "feedback": "Correct option.",
                        }
                    ],
                    "unmatched_answers": [],
                },
            ]
        )
    )
    service = GeminiAssessmentService(client=client, model="test-model")
    page = RasterizedPage(page_number=1, path=image, width=100, height=100)

    mapped = service.map_answers(service.extract_questions([page]), [page])

    box = mapped.mapped_answers[0].answer_regions[0].box_2d
    assert box.model_dump() == tight_box
