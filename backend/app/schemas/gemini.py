"""Structured Output schemas for Google Gemini multimodal AI calls."""

from typing import Literal
from pydantic import BaseModel, Field, model_validator

from app.schemas.question import AnswerRegion, UnmatchedAnswer


class ExtractedQuestion(BaseModel):
    id: str = Field(min_length=1, description="Stable slug such as q11_a.")
    number: str = Field(min_length=1, description="Main printed number, e.g. 11.")
    subpart: str | None = Field(default=None, description="Subpart such as a, if printed.")
    full_label: str = Field(min_length=1, description="Exact printable label, e.g. 11(a).")
    text: str = Field(min_length=1, description="Question wording without the label.")
    max_marks: float = Field(ge=0, description="Allocated marks, or zero if absent.")


class QuestionPaperExtraction(BaseModel):
    questions: list[ExtractedQuestion] = Field(description="Every question in printed sequence.")

    @model_validator(mode="after")
    def question_ids_are_unique(self) -> "QuestionPaperExtraction":
        identifiers = [question.id for question in self.questions]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Question extraction contains duplicate IDs.")
        return self


class MappedAnswer(BaseModel):
    question_id: str = Field(min_length=1, description="Corresponding question ID from question paper")
    status: Literal["answered", "unanswered", "out_of_order"] = Field(description="Status of response")
    transcribed_answer: str | None = Field(default=None, description="Transcribed student response")
    answer_regions: list[AnswerRegion] = Field(default_factory=list, description="Spatial bounding boxes")
    score: float = Field(ge=0, description="Marks awarded based on rubric/correctness (0 if unanswered)")
    is_correct: bool = Field(description="True if answered correctly / full marks, False otherwise")
    feedback: str = Field(min_length=1, description="Concise explanation for marks awarded or deducted")

    @model_validator(mode="after")
    def unanswered_has_no_grounding(self) -> "MappedAnswer":
        if self.status == "unanswered" and (self.transcribed_answer or self.answer_regions):
            raise ValueError("Unanswered mappings cannot contain text or answer regions.")
        # Note: Answered questions may have empty regions if spatial localization was unavailable
        return self


class AnswerSheetExtraction(BaseModel):
    mapped_answers: list[MappedAnswer] = Field(description="Mapping for every question in the exam paper")
    unmatched_answers: list[UnmatchedAnswer] = Field(default_factory=list, description="Extra or unidentified student writing")
