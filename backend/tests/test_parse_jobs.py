"""Tests for background parsing job execution and status reporting."""

import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.api.v1.endpoints.parse as parse_module
from app.main import app
from app.schemas.gemini import AnswerSheetExtraction, MappedAnswer, QuestionPaperExtraction
from app.schemas.gemini import ExtractedQuestion
from app.schemas.job import PIPELINE_STAGES
from app.schemas.question import AnswerRegion, BoundingBox
from app.services.pdf_service import RasterizedPage

FILES = {
    "question_paper": ("paper.pdf", b"%PDF-1.4 fake", "application/pdf"),
    "answer_sheet": ("answer.pdf", b"%PDF-1.4 fake", "application/pdf"),
}


class StubGemini:
    """Mock implementation of Gemini extraction and mapping service for tests."""

    def __init__(self, *_: object, **__: object) -> None:
        pass

    def extract_questions(self, pages):
        return QuestionPaperExtraction(
            questions=[
                ExtractedQuestion(id="q1", number="1", full_label="1", text="Define inertia.", max_marks=2.0),
                ExtractedQuestion(id="q2", number="2", full_label="2", text="State the law.", max_marks=3.0),
            ]
        )

    def map_answers(self, questions, pages):
        return AnswerSheetExtraction(
            mapped_answers=[
                MappedAnswer(
                    question_id="q1",
                    status="answered",
                    transcribed_answer="Resistance to change in motion.",
                    answer_regions=[
                        AnswerRegion(page_number=1, box_2d=BoundingBox(ymin=100, xmin=100, ymax=300, xmax=800))
                    ],
                    score=2.0,
                    is_correct=True,
                    feedback="Correct definition.",
                ),
                MappedAnswer(
                    question_id="q2",
                    status="unanswered",
                    score=0.0,
                    is_correct=False,
                    feedback="Question was not answered.",
                ),
            ],
            unmatched_answers=[],
        )


def _fake_rasterize(source: Path, output_directory: Path, dpi: int = 150, progress=None):
    output_directory.mkdir(parents=True, exist_ok=True)
    pages = []
    for page_number in (1, 2):
        image = output_directory / f"page-{page_number:04d}.jpg"
        image.write_bytes(b"fake jpeg")
        pages.append(RasterizedPage(page_number=page_number, path=image, width=10, height=10))
        if progress is not None:
            progress(page_number, 2)
    return pages


@pytest.fixture
def stubbed_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(parse_module, "rasterize_document", _fake_rasterize)
    monkeypatch.setattr(parse_module, "GeminiAssessmentService", StubGemini)
    monkeypatch.setattr(
        parse_module, "SupabaseService", lambda *a, **k: SimpleNamespace(is_available=False)
    )


def _wait_for_terminal(client: TestClient, job_id: str, timeout: float = 20.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = client.get(f"/api/v1/parse/jobs/{job_id}").json()
        if status["state"] in ("succeeded", "failed"):
            return status
        time.sleep(0.05)
    raise AssertionError("Job did not reach a terminal state in time")


def test_job_accepts_immediately_and_reports_declared_stages(stubbed_pipeline: None) -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/parse/jobs", files=FILES)
        assert response.status_code == 202

        body = response.json()
        assert body["state"] in ("queued", "running")
        assert body["job_id"]
        labels = [stage["label"] for stage in body["stages"]]
        assert "Rasterizing pages" in labels
        assert "Parsing questions" in labels
        assert "Grounding answers" in labels
        assert labels == [stage.label for stage in PIPELINE_STAGES]

        final = _wait_for_terminal(client, body["job_id"])
        assert final["state"] == "succeeded"
        assert final["progress"] == 1.0
        assert final["assessment_id"]
        assert final["persisted"] is False  # Supabase stubbed out


def test_job_result_matches_the_synchronous_contract(stubbed_pipeline: None) -> None:
    with TestClient(app) as client:
        job_id = client.post("/api/v1/parse/jobs", files=FILES).json()["job_id"]
        final = _wait_for_terminal(client, job_id)

        result = client.get(f"/api/v1/parse/jobs/{job_id}/result")
        assert result.status_code == 200
        payload = result.json()
        assert payload["assessment_id"] == final["assessment_id"]
        assert [q["full_label"] for q in payload["questions"]] == ["1", "2"]
        assert payload["total_score"] == 2.0
        assert payload["max_possible_score"] == 5.0
        assert payload["percentage"] == 40.0


def test_event_stream_emits_stages_and_terminates(stubbed_pipeline: None) -> None:
    with TestClient(app) as client:
        job_id = client.post("/api/v1/parse/jobs", files=FILES).json()["job_id"]

        seen_stages: list[str] = []
        final_state: str | None = None
        with client.stream("GET", f"/api/v1/parse/jobs/{job_id}/events") as stream:
            assert stream.status_code == 200
            assert stream.headers["content-type"].startswith("text/event-stream")
            for line in stream.iter_lines():
                if not line.startswith("data: "):
                    continue
                payload = json.loads(line[len("data: ") :])
                seen_stages.append(payload["stage_key"])
                if payload["state"] in ("succeeded", "failed"):
                    final_state = payload["state"]
                    break

        assert final_state == "succeeded"
        assert seen_stages, "the stream produced no status frames"
        assert seen_stages[-1] == PIPELINE_STAGES[-1].key


def test_unknown_job_is_404_on_every_job_route() -> None:
    with TestClient(app) as client:
        assert client.get("/api/v1/parse/jobs/does-not-exist").status_code == 404
        assert client.get("/api/v1/parse/jobs/does-not-exist/result").status_code == 404
        assert client.get("/api/v1/parse/jobs/does-not-exist/events").status_code == 404


def test_job_rejects_unsupported_document_type() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/parse/jobs",
            files={
                "question_paper": ("document.txt", b"plain text", "text/plain"),
                "answer_sheet": ("answer.pdf", b"%PDF-1.4", "application/pdf"),
            },
        )
    assert response.status_code == 415


def test_failed_job_surfaces_its_specific_status_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that upstream API errors are propagated with appropriate HTTP status codes."""
    from app.services.gemini_service import GeminiQuotaError

    class QuotaGemini(StubGemini):
        def extract_questions(self, pages):
            raise GeminiQuotaError()

    monkeypatch.setattr(parse_module, "rasterize_document", _fake_rasterize)
    monkeypatch.setattr(parse_module, "GeminiAssessmentService", QuotaGemini)
    monkeypatch.setattr(
        parse_module, "SupabaseService", lambda *a, **k: SimpleNamespace(is_available=False)
    )

    with TestClient(app) as client:
        job_id = client.post("/api/v1/parse/jobs", files=FILES).json()["job_id"]
        final = _wait_for_terminal(client, job_id)
        assert final["state"] == "failed"
        assert final["error_status"] == 429
        assert "quota" in (final["error"] or "").lower()

        result = client.get(f"/api/v1/parse/jobs/{job_id}/result")
        assert result.status_code == 429


def test_synchronous_parse_does_not_block_the_event_loop(stubbed_pipeline: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure synchronous parse operations execute in a thread pool without blocking event loop."""
    import threading

    started = threading.Event()

    def slow_rasterize(source: Path, output_directory: Path, dpi: int = 150, progress=None):
        started.set()
        time.sleep(0.4)
        return _fake_rasterize(source, output_directory, dpi, progress)

    monkeypatch.setattr(parse_module, "rasterize_document", slow_rasterize)

    with TestClient(app) as client:
        health_latencies: list[float] = []

        def hammer_health() -> None:
            started.wait(timeout=5)
            for _ in range(4):
                begin = time.perf_counter()
                client.get("/api/v1/health")
                health_latencies.append(time.perf_counter() - begin)

        watcher = threading.Thread(target=hammer_health)
        watcher.start()
        assert client.post("/api/v1/parse", files=FILES).status_code == 200
        watcher.join()

    assert health_latencies, "health probe never ran"
    assert max(health_latencies) < 0.3, (
        f"/health stalled behind /parse (worst {max(health_latencies):.3f}s) - "
        "the pipeline is running on the event loop"
    )
