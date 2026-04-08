from __future__ import annotations

from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from app.schemas.file import FileRead


class SearchRequest(BaseModel):
    keyword: Optional[str] = None
    source_ids: Optional[List[int]] = None
    extensions: Optional[List[str]] = None
    min_size: Optional[int] = Field(default=None, ge=0)
    max_size: Optional[int] = Field(default=None, ge=0)
    sort_by: str = Field(default="updated_at")
    sort_order: str = Field(default="desc")
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class SearchResponse(BaseModel):
    total: int
    page: int
    size: int
    backend: str = "database"
    items: List[FileRead]
