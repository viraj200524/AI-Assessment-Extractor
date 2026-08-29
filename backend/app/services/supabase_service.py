"""Supabase persistence service for assessments, questions, and storage assets."""

from typing import Any
from uuid import UUID, uuid4

from app.core.config import get_settings
from app.core.database import get_supabase_client
from app.core.logger import logger
from app.schemas.question import QuestionItem, UnmatchedAnswer


class SupabaseServiceError(RuntimeError):
    """Database or Storage operation failed."""


class AssessmentNotFoundError(SupabaseServiceError):
    """The requested assessment does not exist. Distinct from a backend failure."""


class SupabaseService:
    def __init__(self, client: Any | None = None) -> None:
        self.settings = get_settings()
        self.client = client if client is not None else get_supabase_client()

    @property
    def is_available(self) -> bool:
        return self.client is not None

    def upload_document(
        self,
        bucket: str,
        file_name: str,
        data: bytes,
        content_type: str = "application/pdf",
    ) -> str:
        """Upload a binary file to a private Supabase Storage bucket and return its storage path."""
        if not self.is_available:
            raise SupabaseServiceError("Supabase is not configured.")

        storage_path = f"{uuid4()}_{file_name}"
        try:
            self.client.storage.from_(bucket).upload(
                path=storage_path,
                file=data,
                file_options={"content-type": content_type, "upsert": "true"},
            )
            logger.info(f"Uploaded file to storage: {bucket}/{storage_path}")
            return storage_path
        except Exception as exc:
            logger.error(f"Failed to upload {file_name} to bucket {bucket}: {exc}")
            raise SupabaseServiceError(f"Storage upload error: {exc}") from exc

    def create_signed_url(self, bucket: str, file_path: str, expires_in: int = 86400) -> str:
        """Generate a signed URL for reading a private storage asset (default 24h)."""
        if not self.is_available:
            raise SupabaseServiceError("Supabase is not configured.")

        try:
            response = self.client.storage.from_(bucket).create_signed_url(
                path=file_path,
                expires_in=expires_in,
            )
            if isinstance(response, dict):
                signed_url = response.get("signedURL") or response.get("signedUrl") or response.get("url")
            else:
                signed_url = getattr(response, "signed_url", None) or getattr(response, "url", None)

            if not signed_url:
                # Fallback to public URL format if signedURL key not directly in root
                signed_url = f"{self.settings.supabase_url}/storage/v1/object/sign/{bucket}/{file_path}"

            return signed_url
        except Exception as exc:
            logger.error(f"Failed to create signed URL for {bucket}/{file_path}: {exc}")
            return f"{self.settings.supabase_url}/storage/v1/object/public/{bucket}/{file_path}"

    def save_assessment_record(
        self,
        assessment_id: str,
        title: str,
        question_paper_path: str,
        answer_sheet_path: str,
        page_count: int,
        total_score: float,
        max_score: float,
        percentage: float,
        questions: list[QuestionItem],
        unmatched_answers: list[UnmatchedAnswer] | None = None,
    ) -> str:
        """Persist the assessment, its questions, and its unmatched answers into PostgreSQL."""
        if not self.is_available:
            raise SupabaseServiceError("Supabase is not configured.")

        try:
            # 1. Insert parent assessment record
            assessment_data = {
                "id": assessment_id,
                "title": title,
                "question_paper_url": question_paper_path,
                "answer_sheet_url": answer_sheet_path,
                "page_count": page_count,
                "total_score": round(total_score, 2),
                "max_score": round(max_score, 2),
                "percentage": round(percentage, 2),
            }
            self.client.table("assessments").upsert(assessment_data).execute()

            # 2. Insert question records.
            # order_index preserves the printed sequence (FR-03). created_at cannot: every
            # row in this batch shares one transaction timestamp, so ordering by it is an
            # unspecified tiebreak that an upsert-update can silently reshuffle.
            question_rows = []
            for order_index, q in enumerate(questions):
                question_rows.append(
                    {
                        "assessment_id": assessment_id,
                        "question_key": q.id,
                        "order_index": order_index,
                        "full_label": q.full_label,
                        "question_text": q.text,
                        "max_marks": round(q.max_marks, 2),
                        "obtained_score": round(q.evaluation.score, 2),
                        "status": q.status,
                        # Stored, not re-derived: score >= max_marks cannot express an answer
                        # the examiner judged substantially correct on partial credit.
                        "is_correct": q.evaluation.is_correct,
                        "transcribed_answer": q.transcribed_answer,
                        "feedback": q.evaluation.feedback,
                        "answer_regions": [r.model_dump(mode="json") for r in q.answer_regions],
                    }
                )

            if question_rows:
                self.client.table("questions").upsert(question_rows, on_conflict="assessment_id, question_key").execute()

            # 3. Insert unmatched student writing (FR-09).
            unmatched_rows = []
            for order_index, unmatched in enumerate(unmatched_answers or []):
                unmatched_rows.append(
                    {
                        "assessment_id": assessment_id,
                        "answer_key": unmatched.id,
                        "order_index": order_index,
                        "page_number": unmatched.page_number,
                        "box_2d": unmatched.box_2d.model_dump(mode="json"),
                        "transcribed_text": unmatched.transcribed_text,
                        "reason": unmatched.reason,
                    }
                )

            if unmatched_rows:
                self.client.table("unmatched_answers").upsert(
                    unmatched_rows, on_conflict="assessment_id, answer_key"
                ).execute()

            logger.info(
                f"Persisted assessment {assessment_id} with {len(question_rows)} questions "
                f"and {len(unmatched_rows)} unmatched answer(s)."
            )
            return assessment_id
        except Exception as exc:
            logger.error(f"Failed to persist assessment {assessment_id}: {exc}")
            raise SupabaseServiceError(f"Database insertion failed: {exc}") from exc

    def fetch_assessment(self, assessment_id: str) -> dict[str, Any]:
        """Fetch full assessment record with its questions and signed document URLs."""
        if not self.is_available:
            raise SupabaseServiceError("Supabase is not configured.")

        # A syntactically invalid id cannot name a row; treat it as missing rather than
        # letting PostgREST raise 22P02 and surface as a 500.
        try:
            UUID(assessment_id)
        except (ValueError, AttributeError, TypeError):
            raise AssessmentNotFoundError(f"Assessment {assessment_id} not found.") from None

        try:
            # limit(1) rather than single(): single() raises PGRST116 on zero rows, which
            # made the not-found branch below unreachable and returned 500 instead of 404.
            assessment_res = (
                self.client.table("assessments").select("*").eq("id", assessment_id).limit(1).execute()
            )
            rows = assessment_res.data or []
            if not rows:
                raise AssessmentNotFoundError(f"Assessment {assessment_id} not found.")

            assessment_row = rows[0]
            questions_res = (
                self.client.table("questions")
                .select("*")
                .eq("assessment_id", assessment_id)
                .order("order_index")
                .order("created_at")
                .execute()
            )
            unmatched_res = (
                self.client.table("unmatched_answers")
                .select("*")
                .eq("assessment_id", assessment_id)
                .order("order_index")
                .execute()
            )

            # Generate signed URL for answer sheet
            answer_path = assessment_row.get("answer_sheet_url", "")
            signed_answer_url = self.create_signed_url(
                bucket=self.settings.supabase_answer_sheets_bucket,
                file_path=answer_path,
            )

            # Determine document type from path
            doc_type = "application/pdf"
            if answer_path.lower().endswith(".png"):
                doc_type = "image/png"
            elif answer_path.lower().endswith((".jpg", ".jpeg")):
                doc_type = "image/jpeg"

            # Reconstruct QuestionItem structures
            questions_list = []
            for row in questions_res.data or []:
                obtained = float(row.get("obtained_score", 0.0))
                max_marks = float(row.get("max_marks", 0.0))
                questions_list.append(
                    {
                        "id": row.get("question_key"),
                        "number": row.get("question_key", "").replace("q", "").split("_")[0],
                        "subpart": row.get("question_key", "").split("_")[1] if "_" in row.get("question_key", "") else None,
                        "full_label": row.get("full_label"),
                        "text": row.get("question_text"),
                        "max_marks": max_marks,
                        "status": row.get("status"),
                        "transcribed_answer": row.get("transcribed_answer"),
                        "evaluation": {
                            "score": obtained,
                            "max_marks": max_marks,
                            "is_correct": bool(row.get("is_correct", False)),
                            "feedback": row.get("feedback") or "Evaluation complete.",
                        },
                        "answer_regions": row.get("answer_regions") or [],
                    }
                )

            # Reconstruct UnmatchedAnswer structures (FR-09)
            unmatched_list = []
            for row in unmatched_res.data or []:
                unmatched_list.append(
                    {
                        "id": row.get("answer_key"),
                        "page_number": int(row.get("page_number", 1)),
                        "box_2d": row.get("box_2d") or {},
                        "transcribed_text": row.get("transcribed_text") or "",
                        "reason": row.get("reason") or "Unmapped student writing.",
                    }
                )

            return {
                "assessment": {
                    "assessment_id": assessment_row.get("id"),
                    "title": assessment_row.get("title"),
                    "total_score": float(assessment_row.get("total_score", 0.0)),
                    "max_possible_score": float(assessment_row.get("max_score", 0.0)),
                    "percentage": float(assessment_row.get("percentage", 0.0)),
                    "questions": questions_list,
                    "unmatched_answers": unmatched_list,
                },
                "answer_document_url": signed_answer_url,
                "answer_document_type": doc_type,
            }
        except AssessmentNotFoundError:
            raise
        except Exception as exc:
            logger.error(f"Error fetching assessment {assessment_id}: {exc}")
            raise

    def list_all_assessments(self) -> list[dict[str, Any]]:
        """List summary of all historical assessments."""
        if not self.is_available:
            return []
        try:
            res = self.client.table("assessments").select("*").order("created_at", desc=True).execute()
            return res.data or []
        except Exception as exc:
            logger.error(f"Error listing assessments: {exc}")
            return []

    def delete_assessment(self, assessment_id: str) -> bool:
        """Delete an assessment record (cascading to questions).

        Raises AssessmentNotFoundError when nothing matched, so the API can answer 404
        instead of reporting success for an id that never existed.
        """
        if not self.is_available:
            raise SupabaseServiceError("Supabase is not configured.")

        try:
            UUID(assessment_id)
        except (ValueError, AttributeError, TypeError):
            raise AssessmentNotFoundError(f"Assessment {assessment_id} not found.") from None

        try:
            response = self.client.table("assessments").delete().eq("id", assessment_id).execute()
        except Exception as exc:
            logger.error(f"Error deleting assessment {assessment_id}: {exc}")
            raise SupabaseServiceError(f"Delete failed: {exc}") from exc

        if not (response.data or []):
            raise AssessmentNotFoundError(f"Assessment {assessment_id} not found.")
        logger.info(f"Deleted assessment {assessment_id}")
        return True
