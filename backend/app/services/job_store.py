"""In-process registry of parsing jobs, so the client can watch pipeline stages live.

Scope note: this store is per-process. It is the right shape for a single uvicorn worker
(the default deployment here). Running multiple workers or replicas requires moving this
state to Redis or Postgres, otherwise a poll can land on a worker that never saw the job.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from app.core.logger import logger
from app.schemas.assessment import AssessmentResponse
from app.schemas.job import PIPELINE_STAGES, STAGE_INDEX, JobStatus

_TERMINAL_STATES = {"succeeded", "failed"}


@dataclass
class JobRecord:
    job_id: str
    state: str = "queued"
    stage_key: str = PIPELINE_STAGES[0].key
    detail: str | None = None
    assessment_id: str | None = None
    persisted: bool = False
    error: str | None = None
    error_status: int | None = None
    result: AssessmentResponse | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 0

    def to_status(self) -> JobStatus:
        stage_index = STAGE_INDEX.get(self.stage_key, 0)
        if self.state == "succeeded":
            progress = 1.0
        else:
            progress = min(stage_index / len(PIPELINE_STAGES), 1.0)
        stage = PIPELINE_STAGES[stage_index]
        return JobStatus(
            job_id=self.job_id,
            state=self.state,  # type: ignore[arg-type]
            stages=list(PIPELINE_STAGES),
            stage_index=stage_index,
            stage_key=stage.key,
            stage_label=stage.label,
            detail=self.detail,
            progress=round(progress, 3),
            assessment_id=self.assessment_id,
            persisted=self.persisted,
            error=self.error,
            error_status=self.error_status,
        )


class JobStore:
    """Thread-safe job registry with TTL-based eviction."""

    def __init__(self, ttl_seconds: float = 3600.0, max_jobs: int = 200) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = threading.Lock()
        self._ttl_seconds = ttl_seconds
        self._max_jobs = max_jobs

    def create(self) -> JobRecord:
        job = JobRecord(job_id=str(uuid4()))
        with self._lock:
            self._prune_locked()
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **fields: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in fields.items():
                setattr(job, key, value)
            job.updated_at = time.time()
            job.version += 1

    def set_stage(self, job_id: str, stage_key: str, detail: str | None = None) -> None:
        self.update(job_id, state="running", stage_key=stage_key, detail=detail)

    def fail(self, job_id: str, message: str, status_code: int) -> None:
        self.update(job_id, state="failed", error=message, error_status=status_code, detail=None)

    def succeed(self, job_id: str, result: AssessmentResponse, persisted: bool) -> None:
        self.update(
            job_id,
            state="succeeded",
            stage_key=PIPELINE_STAGES[-1].key,
            detail=None,
            result=result,
            assessment_id=result.assessment_id,
            persisted=persisted,
        )

    def _prune_locked(self) -> None:
        cutoff = time.time() - self._ttl_seconds
        expired = [
            job_id
            for job_id, job in self._jobs.items()
            if job.updated_at < cutoff and job.state in _TERMINAL_STATES
        ]
        for job_id in expired:
            del self._jobs[job_id]

        if len(self._jobs) >= self._max_jobs:
            # Evict the oldest finished jobs first; never evict work still in flight.
            finished = sorted(
                (job for job in self._jobs.values() if job.state in _TERMINAL_STATES),
                key=lambda job: job.updated_at,
            )
            for job in finished[: len(self._jobs) - self._max_jobs + 1]:
                del self._jobs[job.job_id]
        if expired:
            logger.info(f"Evicted {len(expired)} expired parsing job(s).")


job_store = JobStore()
