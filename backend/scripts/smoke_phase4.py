"""Run a live end-to-end Phase 4 smoke test with Gemini Vision and Supabase persistence."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import pymupdf
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app
from app.services.supabase_service import SupabaseService


def create_pdf(path: Path, text: str) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text, fontsize=16)
    document.save(path)
    document.close()


def main() -> int:
    with TemporaryDirectory(prefix="vedai-phase4-") as temporary_directory:
        workspace = Path(temporary_directory)
        qp_file = workspace / "Physics_Test.pdf"
        ans_file = workspace / "Student_Response.pdf"

        create_pdf(qp_file, "11(a). State Ohm's Law. (2 marks)\n11(b). Define electric power. (2 marks)")
        create_pdf(ans_file, "11(a). V = IR, current is proportional to voltage.\n11(b). Power is energy per unit time, P = VI.")

        print("1. Sending POST /api/v1/parse multipart request...")
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/parse",
                files={
                    "question_paper": ("Physics_Test.pdf", qp_file.read_bytes(), "application/pdf"),
                    "answer_sheet": ("Student_Response.pdf", ans_file.read_bytes(), "application/pdf"),
                },
            )

        if response.status_code != 200:
            print(f"Phase 4 parse failed with HTTP {response.status_code}: {response.text}")
            return 1

        payload = response.json()
        assessment_id = payload["assessment_id"]
        print(f"2. Successfully parsed and graded: ID={assessment_id}, score={payload['total_score']}/{payload['max_possible_score']} ({payload['percentage']}%)")
        print(f"   Questions count: {len(payload['questions'])}")
        for q in payload["questions"]:
            print(f"   - Q {q['full_label']}: status={q['status']}, score={q['evaluation']['score']}/{q['max_marks']}, regions={len(q['answer_regions'])}")

        print("3. Testing Supabase retrieval...")
        supabase = SupabaseService()
        if supabase.is_available:
            record = supabase.fetch_assessment(assessment_id)
            print(f"4. Retrieved assessment from Supabase successfully!")
            print(f"   Title: {record['assessment']['title']}")
            print(f"   Signed Answer Doc URL: {record['answer_document_url'][:60]}...")
            print(f"   Questions in DB: {len(record['assessment']['questions'])}")
        else:
            print("Supabase is not configured; skipped direct DB fetch.")

    print("\nPhase 4 Live End-to-End Smoke Test Passed Successfully!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
