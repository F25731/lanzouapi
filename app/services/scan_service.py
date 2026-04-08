from __future__ import annotations

import logging
from datetime import datetime
from pathlib import PurePosixPath
from typing import List
from typing import Optional

from sqlalchemy.orm import Session

from app.models.entities import ScanJob
from app.models.enums import ScanJobStatus
from app.models.enums import ScanMode
from app.models.enums import SourceStatus
from app.providers.registry import provider_registry
from app.repositories.file_repository import FileRepository
from app.repositories.scan_job_repository import ScanJobRepository
from app.repositories.source_repository import FolderRepository
from app.repositories.source_repository import SourceRepository
from app.utils.rate_limiter import source_rate_limiter
from app.utils.serialization import dumps_json
from app.utils.serialization import loads_json
from app.services.search_index_service import SearchIndexService


logger = logging.getLogger(__name__)


class ScanService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.source_repository = SourceRepository(db)
        self.folder_repository = FolderRepository(db)
        self.file_repository = FileRepository(db)
        self.job_repository = ScanJobRepository(db)
        self.search_index_service = SearchIndexService(self.file_repository)

    def enqueue_scan(
        self,
        source_id: int,
        provider_folder_id: Optional[str],
        mode: ScanMode,
        requested_by: str = "api",
    ) -> ScanJob:
        source = self.source_repository.get_source(source_id)
        if source is None:
            raise LookupError("source not found")
        if not source.is_enabled:
            raise ValueError("source is disabled")

        job = ScanJob(
            source_id=source_id,
            target_provider_folder_id=provider_folder_id,
            mode=mode,
            status=ScanJobStatus.PENDING,
            requested_by=requested_by,
            checkpoint_json=None,
        )
        self.job_repository.save(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def run_next_pending_job(self) -> bool:
        job = self.job_repository.get_next_pending_job()
        if job is None:
            return False
        self.run_job(job.id)
        return True

    def run_job(self, job_id: int) -> ScanJob:
        job = self.job_repository.get_by_id(job_id)
        if job is None:
            raise LookupError("scan job not found")

        source = self.source_repository.get_source(job.source_id)
        if source is None:
            raise LookupError("source not found")

        provider = provider_registry.get(source.adapter_type)
        scan_started_marker = datetime.utcnow()

        try:
            self.job_repository.mark_running(job)
            provider.login(source)
            source.last_login_at = datetime.utcnow()
            self.db.add(source)
            self.db.commit()

            queue = loads_json(job.checkpoint_json, [])
            if not queue:
                queue = [
                    {
                        "provider_folder_id": job.target_provider_folder_id
                        or source.root_folder_id,
                        "parent_local_id": None,
                        "name": "root",
                        "full_path": "/",
                        "depth": 0,
                        "share_url": None,
                    }
                ]

            processed_folders = 0
            processed_files = 0
            processed_file_ids = []
            deleted_file_ids = []

            while queue:
                item = queue.pop(0)
                current_folder_id = item.get("provider_folder_id")
                parent_local_id = item.get("parent_local_id")
                name = item.get("name") or "root"
                full_path = item.get("full_path") or "/"
                depth = int(item.get("depth", 0))

                local_folder = None
                if current_folder_id:
                    local_folder = self.folder_repository.upsert_folder(
                        source_id=source.id,
                        provider_folder_id=current_folder_id,
                        parent_id=parent_local_id,
                        name=name,
                        full_path=full_path,
                        share_url=item.get("share_url"),
                        depth=depth,
                    )

                cursor = None
                while True:
                    source_rate_limiter.wait(
                        source_key=str(source.id),
                        rate_limit_per_minute=source.rate_limit_per_minute,
                    )
                    listing = provider.list_folder(
                        source=source,
                        folder_id=current_folder_id,
                        cursor=cursor,
                    )

                    for remote_folder in listing.folders:
                        child_path = remote_folder.full_path or _join_path(
                            full_path, remote_folder.name
                        )
                        self.folder_repository.upsert_folder(
                            source_id=source.id,
                            provider_folder_id=remote_folder.provider_folder_id,
                            parent_id=local_folder.id if local_folder else None,
                            name=remote_folder.name,
                            full_path=child_path,
                            share_url=remote_folder.share_url,
                            depth=depth + 1,
                        )
                        queue.append(
                            {
                                "provider_folder_id": remote_folder.provider_folder_id,
                                "parent_local_id": local_folder.id if local_folder else None,
                                "name": remote_folder.name,
                                "full_path": child_path,
                                "depth": depth + 1,
                                "share_url": remote_folder.share_url,
                            }
                        )
                        processed_folders += 1

                    for remote_file in listing.files:
                        file_record = self.file_repository.upsert_file(
                            source_id=source.id,
                            folder_id=local_folder.id if local_folder else None,
                            provider_file_id=remote_file.provider_file_id,
                            file_name=remote_file.file_name,
                            file_path=remote_file.file_path,
                            size_bytes=remote_file.size_bytes,
                            share_url=remote_file.share_url,
                            source_updated_at=remote_file.updated_at,
                        )
                        processed_file_ids.append(file_record.id)
                        processed_files += 1

                    job.progress_current = processed_files + processed_folders
                    job.checkpoint_json = dumps_json(queue)
                    self.db.add(job)
                    self.db.commit()

                    cursor = listing.next_cursor
                    if not cursor:
                        break

            if job.mode == ScanMode.FULL and not job.target_provider_folder_id:
                deleted_file_ids = self.file_repository.mark_not_seen_as_deleted(
                    source.id,
                    scan_started_marker,
                )

            source.last_sync_at = datetime.utcnow()
            source.status = SourceStatus.ACTIVE
            source.last_error = None
            self.db.add(source)

            summary = {
                "processed_folders": processed_folders,
                "processed_files": processed_files,
                "completed_at": datetime.utcnow().isoformat(),
            }
            try:
                indexed_count = self.search_index_service.sync_files_by_ids(
                    processed_file_ids
                )
                deleted_count = self.search_index_service.delete_files_by_ids(
                    deleted_file_ids
                )
                summary["search_index_indexed"] = indexed_count
                summary["search_index_deleted"] = deleted_count
            except Exception as sync_exc:
                logger.exception("search index sync failed after scan job %s", job.id)
                summary["search_index_error"] = str(sync_exc)
            job.progress_total = job.progress_current
            job.checkpoint_json = dumps_json([])
            self.job_repository.mark_completed(job, summary_json=dumps_json(summary))
            self.db.add(source)
            self.db.commit()
            self.db.refresh(job)
            return job
        except Exception as exc:
            source.status = SourceStatus.ERROR
            source.last_error = str(exc)
            self.db.add(source)
            self.job_repository.mark_failed(job, str(exc))
            self.db.commit()
            raise

    def list_recent_jobs(self, limit: int = 20) -> List[ScanJob]:
        return self.job_repository.list_recent(limit=limit)


def _join_path(prefix: str, name: str) -> str:
    return str(PurePosixPath(prefix) / name)
