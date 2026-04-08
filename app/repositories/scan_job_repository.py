from __future__ import annotations

from datetime import datetime
from typing import Optional
from typing import List

from sqlalchemy.orm import Session

from app.models.entities import ScanJob
from app.models.enums import ScanJobStatus


class ScanJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, job: ScanJob) -> ScanJob:
        self.db.add(job)
        self.db.flush()
        self.db.refresh(job)
        return job

    def get_by_id(self, job_id: int) -> Optional[ScanJob]:
        return self.db.query(ScanJob).filter(ScanJob.id == job_id).first()

    def get_next_pending_job(self) -> Optional[ScanJob]:
        return (
            self.db.query(ScanJob)
            .filter(ScanJob.status == ScanJobStatus.PENDING)
            .order_by(ScanJob.created_at.asc(), ScanJob.id.asc())
            .first()
        )

    def list_recent(self, limit: int = 20) -> List[ScanJob]:
        return (
            self.db.query(ScanJob)
            .order_by(ScanJob.created_at.desc(), ScanJob.id.desc())
            .limit(limit)
            .all()
        )

    def mark_running(self, job: ScanJob) -> ScanJob:
        job.status = ScanJobStatus.RUNNING
        job.started_at = datetime.utcnow()
        job.error_message = None
        self.db.add(job)
        self.db.flush()
        return job

    def mark_completed(self, job: ScanJob, summary_json: Optional[str] = None) -> ScanJob:
        job.status = ScanJobStatus.COMPLETED
        job.finished_at = datetime.utcnow()
        job.summary_json = summary_json
        job.error_message = None
        self.db.add(job)
        self.db.flush()
        return job

    def mark_failed(self, job: ScanJob, error_message: str) -> ScanJob:
        job.status = ScanJobStatus.FAILED
        job.finished_at = datetime.utcnow()
        job.error_message = error_message
        self.db.add(job)
        self.db.flush()
        return job
