"""Schemas for the asynchronous parsing job that backs the multi-stage progress UI."""

from typing import Literal

from pydantic import BaseModel, Field

JobState = Literal["queued", "running", "succeeded", "failed"]


class JobStage(BaseModel):
    key: str = Field(description="Stable stage identifier, e.g. 'rasterizing'")
    label: str = Field(description="Human-readable stage label shown in the progress UI")


#: Pipeline execution stages in sequential order
PIPELINE_STAGES: list[JobStage] = [
    JobStage(key="uploading", label="Uploading documents"),
    JobStage(key="rasterizing", label="Rasterizing pages"),
    JobStage(key="parsing_questions", label="Parsing questions"),
    JobStage(key="grounding_answers", label="Grounding answers"),
    JobStage(key="persisting", label="Saving results"),
]

STAGE_INDEX: dict[str, int] = {stage.key: index for index, stage in enumerate(PIPELINE_STAGES)}


class JobStatus(BaseModel):
    """A point-in-time snapshot of a parsing job, polled or streamed by the client."""

    job_id: str
    state: JobState
    stages: list[JobStage] = Field(default_factory=lambda: list(PIPELINE_STAGES))
    stage_index: int = Field(ge=0, description="Index of the stage currently running")
    stage_key: str
    stage_label: str
    detail: str | None = Field(None, description="Sub-stage detail, e.g. 'Rendering page 3 of 4'")
    progress: float = Field(ge=0.0, le=1.0, description="Fraction of the pipeline completed")
    assessment_id: str | None = Field(None, description="Set once the pipeline succeeds")
    persisted: bool = Field(False, description="Whether the result reached Supabase")
    error: str | None = Field(None, description="Client-safe failure message")
    error_status: int | None = Field(None, description="HTTP status the failure maps to")
