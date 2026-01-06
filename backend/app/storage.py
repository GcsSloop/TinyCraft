from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class JobRecord:
    status: str = "queued"
    progress: int = 0
    message: Optional[str] = None
    result_bytes: Optional[bytes] = None
    result_name: Optional[str] = None
    result_mime: Optional[str] = None
    events: asyncio.Queue = field(default_factory=asyncio.Queue)


class JobStore:
    def __init__(self) -> None:
        self._jobs: Dict[str, JobRecord] = {}

    def create(self, job_id: str) -> JobRecord:
        record = JobRecord()
        self._jobs[job_id] = record
        return record

    def get(self, job_id: str) -> Optional[JobRecord]:
        return self._jobs.get(job_id)

    async def push_event(self, job_id: str, event: dict) -> None:
        record = self._jobs.get(job_id)
        if record is None:
            return
        await record.events.put(event)

    async def next_event(self, job_id: str) -> Optional[dict]:
        record = self._jobs.get(job_id)
        if record is None:
            return None
        return await record.events.get()
