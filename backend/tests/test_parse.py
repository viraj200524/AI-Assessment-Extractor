"""Tests for the parse endpoint (/api/v1/parse)."""

from fastapi.testclient import TestClient
from app.main import app


def test_parse_rejects_unsupported_document_type() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/parse",
            files={
                "question_paper": ("document.txt", b"plain text", "text/plain"),
                "answer_sheet": ("answer.pdf", b"pdf content", "application/pdf"),
            },
        )
    assert response.status_code == 415
    assert "Only PDF, PNG, and JPEG" in response.json()["detail"]


def test_parse_rejects_empty_file_upload() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/parse",
            files={
                "question_paper": ("paper.pdf", b"", "application/pdf"),
                "answer_sheet": ("answer.pdf", b"content", "application/pdf"),
            },
        )
    assert response.status_code == 422
