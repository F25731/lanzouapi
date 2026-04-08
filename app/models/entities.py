from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.enums import FileStatus
from app.models.enums import ApiClientStatus
from app.models.enums import AdminUserStatus
from app.models.enums import ScanJobStatus
from app.models.enums import ScanMode
from app.models.enums import SourceStatus


class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class SourceSource(Base, TimestampMixin):
    __tablename__ = "source_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    adapter_type = Column(String(50), nullable=False, default="mock")
    base_url = Column(String(255), nullable=True)
    username = Column(String(120), nullable=False)
    password = Column(String(255), nullable=False)
    root_folder_id = Column(String(120), nullable=True)
    config_json = Column(Text, nullable=True)
    status = Column(
        Enum(SourceStatus),
        nullable=False,
        default=SourceStatus.ACTIVE,
    )
    is_enabled = Column(Boolean, nullable=False, default=True)
    rate_limit_per_minute = Column(Integer, nullable=False, default=30)
    request_timeout_seconds = Column(Integer, nullable=False, default=20)
    last_login_at = Column(DateTime, nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    folders = relationship("SourceFolder", back_populates="source")
    files = relationship("File", back_populates="source")
    scan_jobs = relationship("ScanJob", back_populates="source")


class SourceFolder(Base, TimestampMixin):
    __tablename__ = "source_folders"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "provider_folder_id",
            name="uq_source_folder_provider_id",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(
        Integer,
        ForeignKey("source_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id = Column(
        Integer,
        ForeignKey("source_folders.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider_folder_id = Column(String(120), nullable=False)
    name = Column(String(255), nullable=False)
    full_path = Column(String(1024), nullable=False)
    share_url = Column(String(1024), nullable=True)
    depth = Column(Integer, nullable=False, default=0)
    last_scanned_at = Column(DateTime, nullable=True)

    source = relationship("SourceSource", back_populates="folders")
    parent = relationship("SourceFolder", remote_side=[id])
    files = relationship("File", back_populates="folder")


class File(Base, TimestampMixin):
    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "provider_file_id",
            name="uq_file_source_provider_id",
        ),
        Index("ix_files_name", "file_name"),
        Index("ix_files_normalized_name", "normalized_name"),
        Index("ix_files_source_extension", "source_id", "extension"),
        Index("ix_files_status", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(
        Integer,
        ForeignKey("source_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    folder_id = Column(
        Integer,
        ForeignKey("source_folders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider_file_id = Column(String(120), nullable=False)
    file_name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    extension = Column(String(32), nullable=True, index=True)
    size_bytes = Column(Integer, nullable=True, index=True)
    share_url = Column(String(1024), nullable=True)
    status = Column(
        Enum(FileStatus),
        nullable=False,
        default=FileStatus.ACTIVE,
    )
    source_updated_at = Column(DateTime, nullable=True)
    last_seen_at = Column(DateTime, nullable=True, index=True)
    hot_score = Column(Integer, nullable=False, default=0)

    source = relationship("SourceSource", back_populates="files")
    folder = relationship("SourceFolder", back_populates="files")
    direct_link_cache = relationship(
        "DirectLinkCache",
        back_populates="file",
        uselist=False,
    )
    stats = relationship("FileStat", back_populates="file", uselist=False)


class DirectLinkCache(Base, TimestampMixin):
    __tablename__ = "direct_link_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(
        Integer,
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    direct_url = Column(String(2048), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    fail_count = Column(Integer, nullable=False, default=0)
    hit_count = Column(Integer, nullable=False, default=0)
    miss_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)

    file = relationship("File", back_populates="direct_link_cache")


class FileStat(Base, TimestampMixin):
    __tablename__ = "file_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(
        Integer,
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    download_count = Column(Integer, nullable=False, default=0)
    search_count = Column(Integer, nullable=False, default=0)
    last_downloaded_at = Column(DateTime, nullable=True)
    last_searched_at = Column(DateTime, nullable=True)

    file = relationship("File", back_populates="stats")


class ScanJob(Base, TimestampMixin):
    __tablename__ = "scan_jobs"
    __table_args__ = (
        Index("ix_scan_jobs_status", "status"),
        Index("ix_scan_jobs_source_status", "source_id", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(
        Integer,
        ForeignKey("source_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    folder_id = Column(
        Integer,
        ForeignKey("source_folders.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_provider_folder_id = Column(String(120), nullable=True)
    mode = Column(Enum(ScanMode), nullable=False, default=ScanMode.INCREMENTAL)
    status = Column(
        Enum(ScanJobStatus),
        nullable=False,
        default=ScanJobStatus.PENDING,
    )
    requested_by = Column(String(100), nullable=True)
    checkpoint_json = Column(Text, nullable=True)
    summary_json = Column(Text, nullable=True)
    progress_current = Column(Integer, nullable=False, default=0)
    progress_total = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    source = relationship("SourceSource", back_populates="scan_jobs")


class ApiClient(Base, TimestampMixin):
    __tablename__ = "api_clients"
    __table_args__ = (
        Index("ix_api_clients_status", "status"),
        Index("ix_api_clients_key_prefix", "key_prefix"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_name = Column(String(120), nullable=False, unique=True)
    client_type = Column(String(50), nullable=False, default="robot")
    key_prefix = Column(String(40), nullable=False, unique=True)
    api_key_hash = Column(String(255), nullable=False)
    status = Column(
        Enum(ApiClientStatus),
        nullable=False,
        default=ApiClientStatus.ACTIVE,
    )
    scopes = Column(Text, nullable=True)
    rate_limit_per_min = Column(Integer, nullable=False, default=60)
    ip_whitelist = Column(Text, nullable=True)
    last_used_at = Column(DateTime, nullable=True)


class ApiRequestLog(Base):
    __tablename__ = "api_request_logs"
    __table_args__ = (
        Index("ix_api_request_logs_created_at", "created_at"),
        Index("ix_api_request_logs_client_id", "client_id"),
        Index("ix_api_request_logs_request_path", "request_path"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(
        Integer,
        ForeignKey("api_clients.id", ondelete="SET NULL"),
        nullable=True,
    )
    request_path = Column(String(1024), nullable=False)
    request_method = Column(String(16), nullable=False)
    request_ip = Column(String(64), nullable=True)
    status_code = Column(Integer, nullable=False)
    latency_ms = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AdminUser(Base, TimestampMixin):
    __tablename__ = "admin_users"
    __table_args__ = (Index("ix_admin_users_status", "status"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(120), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    status = Column(
        Enum(AdminUserStatus),
        nullable=False,
        default=AdminUserStatus.ACTIVE,
    )
    last_login_at = Column(DateTime, nullable=True)
