"""Assessment Schemas."""

from pydantic import BaseModel, Field, model_validator
from app.schemas.question import QuestionItem, UnmatchedAnswer


class AssessmentResponse(BaseModel):
    assessment_id: str = Field(min_length=1, description="Unique assessment ID")
    total_score: float = Field(ge=0, description="Sum of obtained scores")
    max_possible_score: float = Field(ge=0, description="Total maximum possible marks")
    percentage: float = Field(ge=0, le=100, description="Overall percentage")
    questions: list[QuestionItem] = Field(default_factory=list, description="Extracted and mapped questions")
    unmatched_answers: list[UnmatchedAnswer] = Field(default_factory=list, description="Unmatched handwritten answers")

    @model_validator(mode="after")
    def validate_totals(self) -> "AssessmentResponse":
        total = sum(question.evaluation.score for question in self.questions)
        maximum = sum(question.max_marks for question in self.questions)
        percentage = (total / maximum * 100) if maximum > 0 else 0
        if round(self.total_score, 2) != round(total, 2) or round(self.max_possible_score, 2) != round(maximum, 2):
            raise ValueError("Assessment totals must equal the sum of question evaluations.")
        if round(self.percentage, 2) != round(percentage, 2):
            raise ValueError("percentage must match total_score / max_possible_score.")
        return self


class AssessmentSummary(BaseModel):
    id: str
    title: str
    page_count: int
    total_score: float
    max_score: float
    percentage: float
    created_at: str
