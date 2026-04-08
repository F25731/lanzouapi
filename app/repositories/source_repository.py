from __future__ import annotations

from datetime import datetime
from typing import Optional
from typing import List

from sqlalchemy.orm import Session

from app.models.entities import SourceFolder
from app.models.entities import SourceSource
from app.models.enums import SourceStatus


class SourceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def count_sources(self) -> int:
        return self.db.query(SourceSource).count()

    def list_sources(self) -> List[SourceSource]:
        return self.db.query(SourceSource).order_by(SourceSource.id.asc()).all()

    def get_source(self, source_id: int) -> Optional[SourceSource]:
        return self.db.query(SourceSource).filter(SourceSource.id == source_id).first()

    def get_source_by_name(self, name: str) -> Optional[SourceSource]:
        return (
            self.db.query(SourceSource).filter(SourceSource.name == name).first()
        )

    def save_source(self, source: SourceSource) -> SourceSource:
        self.db.add(source)
        self.db.flush()
        self.db.refresh(source)
        return source

    def list_enabled_sources(self) -> List[SourceSource]:
        return (
            self.db.query(SourceSource)
            .filter(SourceSource.is_enabled.is_(True))
            .filter(SourceSource.status != SourceStatus.DISABLED)
            .order_by(SourceSource.id.asc())
            .all()
        )

    def update_status(
        self,
        source: SourceSource,
        status: SourceStatus,
        error_message: Optional[str] = None,
    ) -> SourceSource:
        source.status = status
        source.last_error = error_message
        source.updated_at = datetime.utcnow()
        self.db.add(source)
        self.db.flush()
        return source


class FolderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_provider_id(
        self,
        source_id: int,
        provider_folder_id: str,
    ) -> Optional[SourceFolder]:
        return (
            self.db.query(SourceFolder)
            .filter(SourceFolder.source_id == source_id)
            .filter(SourceFolder.provider_folder_id == provider_folder_id)
            .first()
        )

    def upsert_folder(
        self,
        source_id: int,
        provider_folder_id: str,
        parent_id: Optional[int],
        name: str,
        full_path: str,
        share_url: Optional[str],
        depth: int,
    ) -> SourceFolder:
        folder = self.get_by_provider_id(source_id, provider_folder_id)
        if folder is None:
            folder = SourceFolder(
                source_id=source_id,
                provider_folder_id=provider_folder_id,
            )

        folder.parent_id = parent_id
        folder.name = name
        folder.full_path = full_path
        folder.share_url = share_url
        folder.depth = depth
        folder.last_scanned_at = datetime.utcnow()
        self.db.add(folder)
        self.db.flush()
        return folder
