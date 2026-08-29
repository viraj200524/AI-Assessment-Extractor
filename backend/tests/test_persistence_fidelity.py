"""Everything the pipeline produces must survive the database round-trip.

FR-09 (unmatched writing) and the examiner's is_correct verdict were both produced on the
fresh parse and then lost: unmatched answers were never written, and is_correct was
re-derived on read as score >= max_marks.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.schemas.question import (
    AnswerRegion,
    BoundingBox,
    Evaluation,
    QuestionItem,
    UnmatchedAnswer,
)
from app.services.supabase_service import SupabaseService

QUESTION = QuestionItem(
    id="q11_a",
    number="11",
    subpart="a",
    full_label="11(a)",
    text="State Newton's second law.",
    max_marks=4.0,
    status="answered",
    transcribed_answer="Force equals mass times acceleration.",
    # Partial credit the examiner still judged substantially correct: exactly the case the
    # old score >= max_marks derivation got wrong.
    evaluation=Evaluation(score=3.0, max_marks=4.0, is_correct=True, feedback="Substantially correct."),
    answer_regions=[AnswerRegion(page_number=1, box_2d=BoundingBox(ymin=100, xmin=100, ymax=300, xmax=800))],
)

UNMATCHED = [
    UnmatchedAnswer(
        id="unmatched_1",
        page_number=2,
        box_2d=BoundingBox(ymin=800, xmin=100, ymax=950, xmax=800),
        transcribed_text="Rough work: 9.8 * 2 = 19.6",
        reason="Scratchwork not associated with any numbered question.",
    ),
    UnmatchedAnswer(
        id="unmatched_2",
        page_number=3,
        box_2d=BoundingBox(ymin=100, xmin=100, ymax=200, xmax=800),
        transcribed_text="Q99 answer written but no such question exists.",
        reason="Mislabelled response.",
    ),
]


def _mock_client() -> tuple[MagicMock, dict[str, MagicMock]]:
    tables: dict[str, MagicMock] = {
        "assessments": MagicMock(),
        "questions": MagicMock(),
        "unmatched_answers": MagicMock(),
    }
    client = MagicMock()
    client.table.side_effect = lambda name: tables[name]
    return client, tables


def test_unmatched_answers_are_written(monkeypatch) -> None:
    client, tables = _mock_client()
    service = SupabaseService(client=client)

    service.save_assessment_record(
        assessment_id="test-id",
        title="Physics",
        question_paper_path="qp.pdf",
        answer_sheet_path="ans.pdf",
        page_count=3,
        total_score=3.0,
        max_score=4.0,
        percentage=75.0,
        questions=[QUESTION],
        unmatched_answers=UNMATCHED,
    )

    tables["unmatched_answers"].upsert.assert_called_once()
    rows = tables["unmatched_answers"].upsert.call_args.args[0]
    assert [row["answer_key"] for row in rows] == ["unmatched_1", "unmatched_2"]
    assert [row["order_index"] for row in rows] == [0, 1]
    assert rows[0]["page_number"] == 2
    assert rows[0]["box_2d"] == {"ymin": 800, "xmin": 100, "ymax": 950, "xmax": 800}
    assert "Scratchwork" in rows[0]["reason"]


def test_is_correct_is_written_not_derived() -> None:
    client, tables = _mock_client()
    service = SupabaseService(client=client)

    service.save_assessment_record(
        assessment_id="test-id",
        title="Physics",
        question_paper_path="qp.pdf",
        answer_sheet_path="ans.pdf",
        page_count=1,
        total_score=3.0,
        max_score=4.0,
        percentage=75.0,
        questions=[QUESTION],
        unmatched_answers=[],
    )

    rows = tables["questions"].upsert.call_args.args[0]
    assert rows[0]["is_correct"] is True
    assert rows[0]["obtained_score"] == 3.0
    assert rows[0]["max_marks"] == 4.0


def test_no_unmatched_answers_skips_the_write() -> None:
    client, tables = _mock_client()
    SupabaseService(client=client).save_assessment_record(
        assessment_id="test-id",
        title="Physics",
        question_paper_path="qp.pdf",
        answer_sheet_path="ans.pdf",
        page_count=1,
        total_score=0.0,
        max_score=4.0,
        percentage=0.0,
        questions=[QUESTION],
        unmatched_answers=[],
    )
    tables["unmatched_answers"].upsert.assert_not_called()


def test_fetch_restores_unmatched_answers_and_stored_is_correct() -> None:
    client = MagicMock()

    def table_router(name: str):
        table = MagicMock()
        if name == "assessments":
            table.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
                SimpleNamespace(
                    data=[
                        {
                            "id": "test-id",
                            "title": "Physics",
                            "answer_sheet_url": "ans.pdf",
                            "total_score": 3.0,
                            "max_score": 4.0,
                            "percentage": 75.0,
                        }
                    ]
                )
            )
        elif name == "questions":
            table.select.return_value.eq.return_value.order.return_value.order.return_value.execute.return_value = (
                SimpleNamespace(
                    data=[
                        {
                            "question_key": "q11_a",
                            "full_label": "11(a)",
                            "question_text": "State Newton's second law.",
                            "max_marks": 4.0,
                            "obtained_score": 3.0,
                            "status": "answered",
                            "is_correct": True,  # partial credit, still correct
                            "transcribed_answer": "F = ma",
                            "feedback": "Substantially correct.",
                            "answer_regions": [],
                        }
                    ]
                )
            )
        else:
            table.select.return_value.eq.return_value.order.return_value.execute.return_value = (
                SimpleNamespace(
                    data=[
                        {
                            "answer_key": "unmatched_1",
                            "page_number": 2,
                            "box_2d": {"ymin": 800, "xmin": 100, "ymax": 950, "xmax": 800},
                            "transcribed_text": "Rough work",
                            "reason": "Scratchwork.",
                        }
                    ]
                )
            )
        return table

    client.table.side_effect = table_router
    service = SupabaseService(client=client)
    service.create_signed_url = lambda **_: "https://example.test/signed.pdf"  # type: ignore[method-assign]

    payload = service.fetch_assessment("f4b6a7c2-0000-4000-8000-000000000000")
    assessment = payload["assessment"]

    assert len(assessment["unmatched_answers"]) == 1
    assert assessment["unmatched_answers"][0]["id"] == "unmatched_1"
    assert assessment["unmatched_answers"][0]["page_number"] == 2

    evaluation = assessment["questions"][0]["evaluation"]
    # The old read path derived False here (3.0 >= 4.0 is false), overriding the examiner.
    assert evaluation["is_correct"] is True
    assert evaluation["score"] == 3.0
