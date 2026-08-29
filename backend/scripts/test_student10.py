import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.gemini_service import GeminiAssessmentService
from app.services.pdf_service import rasterize_document

def test_student_10():
    qp_file = Path("d:/VIRAJ/vedaAI/Question.pdf")
    ans_file = Path("d:/VIRAJ/vedaAI/Student_10.pdf")
    
    if not qp_file.exists() or not ans_file.exists():
        print("Test files not found.")
        return
        
    with TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        print("Rasterizing documents...")
        qp_pages = rasterize_document(qp_file, workspace / "qp")
        ans_pages = rasterize_document(ans_file, workspace / "ans")
        
        print(f"Rasterized {len(qp_pages)} QP pages and {len(ans_pages)} Answer pages.")
        
        gemini = GeminiAssessmentService()
        print("Extracting questions...")
        extracted_q = gemini.extract_questions(qp_pages)
        print(f"Extracted {len(extracted_q.questions)} questions.")
        
        print("Mapping answers...")
        mapped = gemini.map_answers(extracted_q, ans_pages)
        
        target_ids = {"q21", "q23", "q25", "q28", "q29"}
        for item in mapped.mapped_answers:
            if item.question_id in target_ids or any(item.question_id.startswith(tid) for tid in target_ids):
                print("=" * 60)
                print(f"Question ID: {item.question_id}, Status: {item.status}")
                print(f"Transcribed: {item.transcribed_answer}")
                print(f"Regions: {item.answer_regions}")

if __name__ == "__main__":
    test_student_10()
