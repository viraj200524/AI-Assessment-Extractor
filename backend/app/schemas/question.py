"""Question and Answer Region Schemas."""

from typing import Literal
from pydantic import BaseModel, Field, model_validator


class BoundingBox(BaseModel):
    """A non-empty Gemini normalized [0, 1000] spatial region covering the full answer block."""

    ymin: int = Field(ge=0, le=1000, description="Topmost Y coordinate (0-1000) at or slightly above the start of the answer / question number")
    xmin: int = Field(ge=0, le=1000, description="Leftmost X coordinate (0-1000) to the left of the question number and text")
    ymax: int = Field(ge=0, le=1000, description="Bottommost Y coordinate (0-1000) covering completely below the last line of the entire answer")
    xmax: int = Field(ge=0, le=1000, description="Rightmost X coordinate (0-1000) to the right of the longest line of the answer")

    @model_validator(mode="after")
    def validate_edges(self) -> "BoundingBox":
        if self.ymin >= self.ymax or self.xmin >= self.xmax:
            raise ValueError("Bounding box must have ymin < ymax and xmin < xmax.")
        return self


class AnswerRegion(BaseModel):
    page_number: int = Field(ge=1, description="1-indexed page number")
    box_2d: BoundingBox


class Evaluation(BaseModel):
    score: float = Field(ge=0, description="Marks awarded")
    max_marks: float = Field(ge=0, description="Allocated max marks")
    is_correct: bool = Field(description="Correctness indicator")
    feedback: str = Field(min_length=1, description="Pedagogical feedback explanation")

    @model_validator(mode="after")
    def validate_score(self) -> "Evaluation":
        if self.score > self.max_marks:
            raise ValueError("Evaluation score cannot exceed max_marks.")
        return self


class QuestionItem(BaseModel):
    id: str = Field(min_length=1, description="Unique ID, e.g., 'q11_a'")
    number: str = Field(min_length=1, description="Main question number, e.g., '11'")
    subpart: str | None = Field(None, description="Subpart label, e.g., 'a'")
    full_label: str = Field(min_length=1, description="Display label, e.g., '11(a)'")
    text: str = Field(min_length=1, description="Printed question text")
    max_marks: float = Field(ge=0, description="Allocated marks")
    status: Literal["answered", "unanswered", "out_of_order"] = Field(description="Answer mapping status")
    transcribed_answer: str | None = Field(None, description="Transcribed student handwriting")
    evaluation: Evaluation
    answer_regions: list[AnswerRegion] = Field(default_factory=list, description="Spatial coordinates on answer sheet")

    @model_validator(mode="after")
    def validate_mapping(self) -> "QuestionItem":
        if self.evaluation.max_marks != self.max_marks:
            raise ValueError("evaluation.max_marks must equal question max_marks.")
        if self.status == "unanswered" and (self.transcribed_answer or self.answer_regions):
            raise ValueError("Unanswered questions cannot have an answer or answer regions.")
        return self


class UnmatchedAnswer(BaseModel):
    id: str = Field(min_length=1, description="Unique identifier for unmatched item")
    page_number: int = Field(ge=1, description="1-indexed page number")
    box_2d: BoundingBox
    transcribed_text: str = Field(min_length=1, description="Transcribed text of unmatched writing")
    reason: str = Field(min_length=1, description="Explanation why this response is unmatched")
