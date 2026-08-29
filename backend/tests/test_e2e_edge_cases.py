"""Edge-case tests covering the complete functional requirements matrix (FR-03 to FR-13)."""

import pytest
from pydantic import ValidationError

from app.schemas.assessment import AssessmentResponse
from app.schemas.gemini import ExtractedQuestion, QuestionPaperExtraction
from app.schemas.question import AnswerRegion, BoundingBox, Evaluation, QuestionItem, UnmatchedAnswer


def test_subparts_extracted_as_discrete_questions() -> None:
    """FR-03 & FR-04: Labelled sub-parts like 11(a) and 11(b) must be separate questions."""
    q_paper = QuestionPaperExtraction(
        questions=[
            ExtractedQuestion(
                id="q11_a",
                number="11",
                subpart="a",
                full_label="11(a)",
                text="State Newton's second law of motion.",
                max_marks=2.0,
            ),
            ExtractedQuestion(
                id="q11_b",
                number="11",
                subpart="b",
                full_label="11(b)",
                text="Derive F = ma from rate of change of momentum.",
                max_marks=3.0,
            ),
        ]
    )
    assert len(q_paper.questions) == 2
    assert q_paper.questions[0].full_label == "11(a)"
    assert q_paper.questions[1].full_label == "11(b)"
    assert q_paper.questions[0].max_marks == 2.0
    assert q_paper.questions[1].max_marks == 3.0


def test_unanswered_question_enforces_zero_score_and_no_regions() -> None:
    """FR-08: Unanswered question must have 0 marks and no spatial bounding boxes."""
    q = QuestionItem(
        id="q11_b",
        number="11",
        subpart="b",
        full_label="11(b)",
        text="Derive F = ma.",
        max_marks=3.0,
        status="unanswered",
        transcribed_answer=None,
        evaluation=Evaluation(score=0.0, max_marks=3.0, is_correct=False, feedback="Question was not answered."),
        answer_regions=[],
    )
    assert q.status == "unanswered"
    assert q.evaluation.score == 0.0
    assert len(q.answer_regions) == 0

    # Attempting to attach answer regions to an unanswered question should raise validation error
    with pytest.raises(ValidationError, match="Unanswered questions cannot have an answer"):
        QuestionItem(
            id="q11_b",
            number="11",
            full_label="11(b)",
            text="Derive F = ma.",
            max_marks=3.0,
            status="unanswered",
            transcribed_answer="Some answer",
            evaluation=Evaluation(score=0.0, max_marks=3.0, is_correct=False, feedback="Not empty"),
            answer_regions=[AnswerRegion(page_number=1, box_2d=BoundingBox(ymin=100, xmin=100, ymax=200, xmax=200))],
        )


def test_out_of_order_answer_mapping_and_multi_page_regions() -> None:
    """FR-07, FR-10, FR-11: Out-of-order responses and multi-page answer spans."""
    q = QuestionItem(
        id="q3",
        number="3",
        full_label="3",
        text="Explain electromagnetic induction with diagrams.",
        max_marks=5.0,
        status="out_of_order",
        transcribed_answer="When magnetic flux changes across a closed loop, an EMF is induced.",
        evaluation=Evaluation(score=4.5, max_marks=5.0, is_correct=True, feedback="Good explanation and formula provided."),
        answer_regions=[
            AnswerRegion(page_number=2, box_2d=BoundingBox(ymin=600, xmin=50, ymax=950, xmax=900)),
            AnswerRegion(page_number=3, box_2d=BoundingBox(ymin=50, xmin=50, ymax=400, xmax=900)),
        ],
    )
    assert q.status == "out_of_order"
    assert len(q.answer_regions) == 2
    assert q.answer_regions[0].page_number == 2
    assert q.answer_regions[1].page_number == 3


def test_unmatched_student_writing_isolation() -> None:
    """FR-09: Unmatched or extraneous handwriting is isolated with bounding box and reason."""
    unmatched = UnmatchedAnswer(
        id="unmatched_1",
        page_number=2,
        box_2d=BoundingBox(ymin=800, xmin=100, ymax=950, xmax=800),
        transcribed_text="Rough calculations: 9.8 * 2 = 19.6",
        reason="Scratchwork / rough calculation not associated with any numbered question.",
    )
    assert unmatched.page_number == 2
    assert "Scratchwork" in unmatched.reason


def test_assessment_response_score_and_percentage_mathematical_consistency() -> None:
    """FR-12 & FR-13: Assessment response validates sum of scores and exact percentage."""
    q1 = QuestionItem(
        id="q1",
        number="1",
        full_label="1",
        text="Q1 text",
        max_marks=10.0,
        status="answered",
        transcribed_answer="Ans 1",
        evaluation=Evaluation(score=8.0, max_marks=10.0, is_correct=True, feedback="Well answered."),
        answer_regions=[AnswerRegion(page_number=1, box_2d=BoundingBox(ymin=100, xmin=100, ymax=200, xmax=200))],
    )
    q2 = QuestionItem(
        id="q2",
        number="2",
        full_label="2",
        text="Q2 text",
        max_marks=10.0,
        status="answered",
        transcribed_answer="Ans 2",
        evaluation=Evaluation(score=10.0, max_marks=10.0, is_correct=True, feedback="Perfect."),
        answer_regions=[AnswerRegion(page_number=1, box_2d=BoundingBox(ymin=300, xmin=100, ymax=400, xmax=200))],
    )

    assessment = AssessmentResponse(
        assessment_id="test-asm-1",
        total_score=18.0,
        max_possible_score=20.0,
        percentage=90.0,
        questions=[q1, q2],
        unmatched_answers=[],
    )
    assert assessment.total_score == 18.0
    assert assessment.percentage == 90.0

    # Inconsistent percentage or total must raise validation error
    with pytest.raises(ValidationError, match="Assessment totals must equal the sum"):
        AssessmentResponse(
            assessment_id="test-asm-2",
            total_score=15.0,  # wrong total
            max_possible_score=20.0,
            percentage=75.0,
            questions=[q1, q2],
        )
