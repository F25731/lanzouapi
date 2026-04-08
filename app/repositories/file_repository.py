from __future__ import annotations

from datetime import datetime
from typing import List
from typing import Optional
from typing import Tuple

from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from app.models.entities import DirectLinkCache
from app.models.entities import File
from app.models.entities import FileStat
from app.models.enums import FileStatus
from app.utils.files import extract_extension
from app.utils.files import normalize_name


class FileRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, file_id: int) -> Optional[File]:
        return (
            self.db.query(File)
            .options(
                joinedload(File.source),
                joinedload(File.folder),
                joinedload(File.direct_link_cache),
                joinedload(File.stats),
            )
            .filter(File.id == file_id)
            .first()
        )

    def get_by_ids(self, file_ids: List[int]) -> List[File]:
        if not file_ids:
            return []
        return (
            self.db.query(File)
            .options(
                joinedload(File.source),
                joinedload(File.folder),
                joinedload(File.direct_link_cache),
                joinedload(File.stats),
            )
            .filter(File.id.in_(file_ids))
            .all()
        )

    def get_by_source_provider_id(
        self,
        source_id: int,
        provider_file_id: str,
    ) -> Optional[File]:
        return (
            self.db.query(File)
            .filter(File.source_id == source_id)
            .filter(File.provider_file_id == provider_file_id)
            .first()
        )

    def upsert_file(
        self,
        source_id: int,
        folder_id: Optional[int],
        provider_file_id: str,
        file_name: str,
        file_path: str,
        size_bytes: Optional[int],
        share_url: Optional[str],
        source_updated_at: Optional[datetime],
    ) -> File:
        file_record = self.get_by_source_provider_id(source_id, provider_file_id)
        if file_record is None:
            file_record = File(
                source_id=source_id,
                provider_file_id=provider_file_id,
            )

        file_record.folder_id = folder_id
        file_record.file_name = file_name
        file_record.normalized_name = normalize_name(file_name)
        file_record.file_path = file_path
        file_record.extension = extract_extension(file_name)
        file_record.size_bytes = size_bytes
        file_record.share_url = share_url
        file_record.status = FileStatus.ACTIVE
        file_record.source_updated_at = source_updated_at
        file_record.last_seen_at = datetime.utcnow()
        self.db.add(file_record)
        self.db.flush()
        return file_record

    def search(
        self,
        keyword: Optional[str],
        source_ids: Optional[List[int]],
        extensions: Optional[List[str]],
        min_size: Optional[int],
        max_size: Optional[int],
        sort_by: str,
        sort_order: str,
        page: int,
        size: int,
    ) -> Tuple[int, List[File]]:
        query = (
            self.db.query(File)
            .options(joinedload(File.source), joinedload(File.stats))
            .filter(File.status == FileStatus.ACTIVE)
        )

        if keyword:
            normalized = normalize_name(keyword)
            query = query.filter(
                or_(
                    File.normalized_name.ilike(f"%{normalized}%"),
                    File.file_name.ilike(f"%{keyword}%"),
                )
            )

        if source_ids:
            query = query.filter(File.source_id.in_(source_ids))

        if extensions:
            normalized_extensions = [value.lower() for value in extensions]
            query = query.filter(File.extension.in_(normalized_extensions))

        if min_size is not None:
            query = query.filter(File.size_bytes >= min_size)

        if max_size is not None:
            query = query.filter(File.size_bytes <= max_size)

        sort_column = {
            "size_bytes": File.size_bytes,
            "hot_score": File.hot_score,
            "file_name": File.file_name,
            "updated_at": File.updated_at,
        }.get(sort_by, File.updated_at)

        order_by_clause = sort_column.asc() if sort_order == "asc" else sort_column.desc()
        total = query.count()
        items = (
            query.order_by(order_by_clause, File.id.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )
        return total, items

    def increment_search_counts(self, file_ids: List[int]) -> None:
        if not file_ids:
            return
        existing_stats = {
            stat.file_id: stat
            for stat in self.db.query(FileStat).filter(FileStat.file_id.in_(file_ids)).all()
        }
        now = datetime.utcnow()
        for file_id in file_ids:
            stat = existing_stats.get(file_id)
            if stat is None:
                stat = FileStat(file_id=file_id, download_count=0, search_count=0)
            stat.search_count = stat.search_count or 0
            stat.search_count += 1
            stat.last_searched_at = now
            self.db.add(stat)
        self.db.query(File).filter(File.id.in_(file_ids)).update(
            {File.hot_score: File.hot_score + 1},
            synchronize_session=False,
        )

    def increment_download_count(self, file_id: int) -> None:
        stat = self.db.query(FileStat).filter(FileStat.file_id == file_id).first()
        if stat is None:
            stat = FileStat(file_id=file_id, download_count=0, search_count=0)
        stat.download_count = stat.download_count or 0
        stat.download_count += 1
        stat.last_downloaded_at = datetime.utcnow()
        self.db.add(stat)
        self.db.query(File).filter(File.id == file_id).update(
            {File.hot_score: File.hot_score + 5},
            synchronize_session=False,
        )

    def list_hot_files(self, limit: int = 10) -> List[File]:
        return (
            self.db.query(File)
            .options(joinedload(File.source), joinedload(File.stats))
            .filter(File.status == FileStatus.ACTIVE)
            .order_by(File.hot_score.desc(), File.updated_at.desc())
            .limit(limit)
            .all()
        )

    def list_preheat_candidates(
        self,
        limit: int,
        min_hot_score: int,
        refresh_before: datetime,
    ) -> List[File]:
        return (
            self.db.query(File)
            .options(
                joinedload(File.source),
                joinedload(File.direct_link_cache),
                joinedload(File.stats),
            )
            .outerjoin(DirectLinkCache, DirectLinkCache.file_id == File.id)
            .filter(File.status == FileStatus.ACTIVE)
            .filter(File.hot_score >= min_hot_score)
            .filter(
                or_(
                    DirectLinkCache.id.is_(None),
                    DirectLinkCache.direct_url.is_(None),
                    DirectLinkCache.expires_at.is_(None),
                    DirectLinkCache.expires_at <= refresh_before,
                )
            )
            .order_by(File.hot_score.desc(), File.updated_at.desc())
            .limit(limit)
            .all()
        )

    def list_active_batch(
        self,
        limit: int,
        last_id: int = 0,
        source_id: Optional[int] = None,
    ) -> List[File]:
        query = (
            self.db.query(File)
            .options(joinedload(File.source), joinedload(File.stats))
            .filter(File.status == FileStatus.ACTIVE)
            .filter(File.id > last_id)
        )
        if source_id is not None:
            query = query.filter(File.source_id == source_id)

        return query.order_by(File.id.asc()).limit(limit).all()

    def mark_not_seen_as_deleted(self, source_id: int, seen_after: datetime) -> List[int]:
        deleted_ids = [
            item.id
            for item in self.db.query(File.id)
            .filter(File.source_id == source_id)
            .filter(
                and_(
                    File.last_seen_at.isnot(None),
                    File.last_seen_at < seen_after,
                )
            )
            .all()
        ]
        (
            self.db.query(File)
            .filter(File.source_id == source_id)
            .filter(
                and_(
                    File.last_seen_at.isnot(None),
                    File.last_seen_at < seen_after,
                )
            )
            .update({File.status: FileStatus.DELETED}, synchronize_session=False)
        )
        return deleted_ids

    def stats_overview(self) -> dict:
        active_files = (
            self.db.query(func.count(File.id))
            .filter(File.status == FileStatus.ACTIVE)
            .scalar()
        )
        total_size = (
            self.db.query(func.coalesce(func.sum(File.size_bytes), 0))
            .filter(File.status == FileStatus.ACTIVE)
            .scalar()
        )
        return {
            "active_files": int(active_files or 0),
            "total_size_bytes": int(total_size or 0),
        }
