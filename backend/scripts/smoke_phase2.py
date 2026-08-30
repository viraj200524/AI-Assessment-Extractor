"""Smoke check for Gemini question extraction and answer mapping."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import pymupdf
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app


def create_pdf(path: Path, text: str) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text, fontsize=16)
    document.save(path)
    document.close()


def main() -> int:
    with TemporaryDirectory(prefix="vedai-smoke-") as temporary_directory:
        workspace = Path(temporary_directory)
        question_paper = workspace / "question-paper.pdf"
        answer_sheet = workspace / "answer-sheet.pdf"
        create_pdf(question_paper, "1. What is 2 + 2? (2 marks)")
        create_pdf(answer_sheet, "1. 2 + 2 = 4")

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/parse",
                files={
                    "question_paper": ("question-paper.pdf", question_paper.read_bytes(), "application/pdf"),
                    "answer_sheet": ("answer-sheet.pdf", answer_sheet.read_bytes(), "application/pdf"),
                },
            )
    if response.status_code != 200:
        print(f"Extraction smoke check failed: HTTP {response.status_code}")
        print(response.json().get("detail", "No error detail returned."))
        return 1

    payload = response.json()
    statuses = ",".join(question["status"] for question in payload["questions"])
    first_q = payload["questions"][0] if payload["questions"] else None
    eval_info = f"score={first_q['evaluation']['score']}/{first_q['max_marks']}, feedback='{first_q['evaluation']['feedback']}'" if first_q else "no questions"
    print(
        "Extraction smoke check passed: "
        f"questions={len(payload['questions'])}, statuses={statuses}, "
        f"total={payload['total_score']}/{payload['max_possible_score']} ({payload['percentage']}%), "
        f"{eval_info}, unmatched={len(payload['unmatched_answers'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
