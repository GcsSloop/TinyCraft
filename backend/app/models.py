from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class JobStatus(BaseModel):
    id: str
    status: str
    progress: int
    message: Optional[str] = None


class JobResult(BaseModel):
    id: str
    file_name: Optional[str] = None
    mime: Optional[str] = None
