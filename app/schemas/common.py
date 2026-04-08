from __future__ import annotations

from typing import Generic
from typing import Optional
from typing import TypeVar

from pydantic import BaseModel
from pydantic.generics import GenericModel

T = TypeVar("T")


class MessageResponse(BaseModel):
    message: str


class ApiResponse(GenericModel, Generic[T]):
    code: int
    message: str
    data: Optional[T]
