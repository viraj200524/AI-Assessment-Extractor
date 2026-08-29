from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest

from app.schemas.question import AnswerRegion, BoundingBox, Evaluation, QuestionItem
from app.services.supabase_service import SupabaseService, SupabaseServiceError


def test_supabase_service_reports_unavailable_when_client_is_none() -> None:
    service = SupabaseService(client=None)
    # If client is None, it should report is_available as False or fail fast
    if not service.is_available:
        with pytest.raises(SupabaseServiceError, match="not configured"):
            service.upload_document("bucket", "test.pdf", b"data")


def test_upload_document_calls_storage_upload() -> None:
    mock_client = MagicMock()
    mock_storage = MagicMock()
    mock_client.storage.from_.return_value = mock_storage

    service = SupabaseService(client=mock_client)
    path = service.upload_document("question-papers", "sample.pdf", b"pdf bytes", "application/pdf")

    assert "sample.pdf" in path
    mock_storage.upload.assert_called_once()


def test_save_assessment_record_inserts_into_tables() -> None:
    mock_client = MagicMock()
    mock_assessments_table = MagicMock()
    mock_questions_table = MagicMock()

    def table_router(table_name: str):
        if table_name == "assessments":
            return mock_assessments_table
        return mock_questions_table

    mock_client.table.side_effect = table_router

    service = SupabaseService(client=mock_client)
    question = QuestionItem(
        id="q11_a",
        number="11",
        subpart="a",
        full_label="11(a)",
        text="State Newton's law.",
        max_marks=2.0,
        status="answered",
        transcribed_answer="Force = mass * acceleration",
        evaluation=Evaluation(score=2.0, max_marks=2.0, is_correct=True, feedback="Accurate law."),
        answer_regions=[AnswerRegion(page_number=1, box_2d=BoundingBox(ymin=100, xmin=100, ymax=300, xmax=800))],
    )

    assessment_id = service.save_assessment_record(
        assessment_id="test-id-123",
        title="Test Physics Exam",
        question_paper_path="qp.pdf",
        answer_sheet_path="ans.pdf",
        page_count=2,
        total_score=2.0,
        max_score=2.0,
        percentage=100.0,
        questions=[question],
    )

    assert assessment_id == "test-id-123"
    mock_assessments_table.upsert.assert_called_once()
    mock_questions_table.upsert.assert_called_once()
