from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List
from typing import Optional

from app.models.entities import File
from app.models.entities import SourceSource


@dataclass
class RemoteFolder:
    provider_folder_id: str
    name: str
    full_path: str
    share_url: Optional[str] = None
    depth: int = 0


@dataclass
class RemoteFile:
    provider_file_id: str
    file_name: str
    file_path: str
    size_bytes: Optional[int] = None
    share_url: Optional[str] = None
    updated_at: Optional[datetime] = None


@dataclass
class FolderListing:
    folders: List[RemoteFolder]
    files: List[RemoteFile]
    next_cursor: Optional[str] = None


@dataclass
class DirectLinkResult:
    direct_url: str
    expires_at: Optional[datetime] = None


class SourceProvider(ABC):
    adapter_type = "base"

    @abstractmethod
    def login(self, source: SourceSource) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_folder(
        self,
        source: SourceSource,
        folder_id: Optional[str],
        cursor: Optional[str] = None,
    ) -> FolderListing:
        raise NotImplementedError

    @abstractmethod
    def resolve_direct_link(
        self,
        source: SourceSource,
        file_record: File,
    ) -> DirectLinkResult:
        raise NotImplementedError
