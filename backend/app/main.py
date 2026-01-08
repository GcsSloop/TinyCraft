from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator, Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import RedirectResponse, StreamingResponse
from urllib.parse import quote

from .config import load_config, save_config
from .models import JobResult, JobStatus
from .nano_banana import (
    apply_edit,
    check_connectivity,
    classify_error,
    edit_image,
    extract_error_context,
)
from .storage import JobStore

app = FastAPI(
    title="tiny-craft backend",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)
store = JobStore()
logger = logging.getLogger("uvicorn.error")


@app.get("/", include_in_schema=False)
async def index() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.on_event("startup")
async def startup_check() -> None:
    async def _run() -> None:
        result = await asyncio.to_thread(check_connectivity, load_config())
        status = result.get("status")
        message = result.get("message", "")
        if status == "ok":
            logger.info("Connectivity check ok")
        else:
            logger.warning("Connectivity check failed: %s (%s)", message, status)

    asyncio.create_task(_run())


@app.get("/api/config")
async def get_config() -> dict:
    config = load_config()
    return config.public_dict()


@app.post("/api/config")
async def update_config(payload: dict) -> dict:
    updated = save_config(payload)
    return updated.public_dict()


def _build_region_hint(
    region_x: Optional[int],
    region_y: Optional[int],
    region_width: Optional[int],
    region_height: Optional[int],
) -> str:
    if None in {region_x, region_y, region_width, region_height}:
        return ""
    return (
        "\n\nOnly edit the rectangle region "
        f"(x={region_x}, y={region_y}, width={region_width}, height={region_height}) "
        "in pixels from the top-left corner. Keep all other areas unchanged."
    )


async def run_job(
    job_id: str,
    content: bytes,
    region_start: int,
    region_end: int,
    description: str,
    file_name: Optional[str],
    mime: Optional[str],
) -> None:
    record = store.get(job_id)
    if record is None:
        return
    steps = [
        (10, "queued"),
        (30, "validating"),
        (60, "processing"),
        (90, "finalizing"),
        (100, "completed"),
    ]
    for progress, status in steps:
        await asyncio.sleep(0.6)
        record.status = status
        record.progress = progress
        record.message = f"{status} ({progress}%)"
        await store.push_event(
            job_id,
            {
                "type": "progress",
                "status": record.status,
                "progress": record.progress,
                "message": record.message,
            },
        )

    try:
        record.result_bytes = apply_edit(content, region_start, region_end, description)
        record.result_name = file_name
        record.result_mime = mime
    except Exception as exc:  # pragma: no cover - surfaced to client
        logger.exception("Text job failed: job_id=%s", job_id)
        record.status = "failed"
        record.message = str(exc)
        await store.push_event(
            job_id,
            {
                "type": "failed",
                "message": record.message,
            },
        )
        return
    await store.push_event(job_id, {"type": "completed"})


@app.post("/api/jobs", response_model=JobStatus)
async def create_job(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    region_start: int = Form(...),
    region_end: int = Form(...),
    description: str = Form(...),
    file_name: Optional[str] = Form(None),
    mime: Optional[str] = Form(None),
) -> JobStatus:
    if region_end < region_start:
        raise HTTPException(status_code=400, detail="Invalid region range")
    job_id = uuid.uuid4().hex
    record = store.create(job_id)
    record.status = "queued"
    record.progress = 0
    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=415, detail="Only UTF-8 text is supported")
    if region_end > len(text):
        raise HTTPException(status_code=400, detail="Region exceeds file length")
    selected_name = file_name or file.filename
    selected_mime = mime or file.content_type
    background.add_task(
        run_job,
        job_id,
        raw,
        region_start,
        region_end,
        description,
        selected_name,
        selected_mime,
    )
    return JobStatus(id=job_id, status=record.status, progress=record.progress)


@app.get("/api/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str) -> JobStatus:
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(
        id=job_id,
        status=record.status,
        progress=record.progress,
        message=record.message,
    )


@app.get("/api/jobs/{job_id}/result", response_model=JobResult)
async def get_job_result(job_id: str) -> JobResult:
    record = store.get(job_id)
    if record is None or record.result_bytes is None:
        raise HTTPException(status_code=404, detail="Result not ready")
    return JobResult(
        id=job_id,
        file_name=record.result_name,
        mime=record.result_mime,
    )


@app.get("/api/jobs/{job_id}/result/file")
async def download_result(job_id: str) -> StreamingResponse:
    record = store.get(job_id)
    if record is None or record.result_bytes is None:
        raise HTTPException(status_code=404, detail="Result not ready")
    file_name = record.result_name or "result.bin"
    mime = record.result_mime or "application/octet-stream"
    ascii_name = "".join(ch if 32 <= ord(ch) < 127 else "_" for ch in file_name)
    encoded_name = quote(file_name, safe="")
    headers = {
        "Content-Disposition": (
            f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{encoded_name}'
        ),
    }
    return StreamingResponse(
        iter([record.result_bytes]),
        media_type=mime,
        headers=headers,
    )


async def run_image_job(
    job_id: str,
    image_bytes: bytes,
    prompt: str,
    reference_images: list[bytes],
    file_name: Optional[str],
    mime: Optional[str],
) -> None:
    record = store.get(job_id)
    if record is None:
        return
    steps = [
        (10, "queued"),
        (30, "uploading"),
        (60, "processing"),
        (90, "finalizing"),
        (100, "completed"),
    ]
    for progress, status in steps:
        await asyncio.sleep(0.6)
        record.status = status
        record.progress = progress
        record.message = f"{status} ({progress}%)"
        await store.push_event(
            job_id,
            {
                "type": "progress",
                "status": record.status,
                "progress": record.progress,
                "message": record.message,
            },
        )

    try:
        result = edit_image(image_bytes, prompt, load_config(), reference_images)
    except Exception as exc:  # pragma: no cover - surfaced to client
        kind, message = classify_error(exc)
        logger.error("Image job context: %s", extract_error_context(exc))
        logger.exception("Image job failed: job_id=%s", job_id)
        record.status = "failed"
        record.message = message
        await store.push_event(
            job_id,
            {
                "type": "failed",
                "message": record.message,
                "kind": kind,
            },
        )
        return

    record.result_bytes = result
    record.result_name = file_name
    record.result_mime = mime or "image/png"
    await store.push_event(job_id, {"type": "completed"})


@app.post("/api/image/jobs", response_model=JobStatus)
async def create_image_job(
    background: BackgroundTasks,
    image: UploadFile = File(...),
    references: Optional[list[UploadFile]] = File(
        None,
        description="Optional reference images (0-n). Submit multiple files with the same field name.",
    ),
    description: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
    region_x: Optional[int] = Form(None),
    region_y: Optional[int] = Form(None),
    region_width: Optional[int] = Form(None),
    region_height: Optional[int] = Form(None),
    file_name: Optional[str] = Form(None),
    mime: Optional[str] = Form(None),
) -> JobStatus:
    config = load_config()
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Only image uploads are supported")
    if references:
        for ref in references:
            if not ref.content_type or not ref.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=415, detail="Only image uploads are supported"
                )
    if (description is None) and (prompt is None):
        raise HTTPException(status_code=400, detail="Missing description")
    if any(
        value is not None
        for value in (region_x, region_y, region_width, region_height)
    ) and None in {region_x, region_y, region_width, region_height}:
        raise HTTPException(status_code=400, detail="Region parameters are incomplete")
    if region_width is not None and region_width <= 0:
        raise HTTPException(status_code=400, detail="Region width must be positive")
    if region_height is not None and region_height <= 0:
        raise HTTPException(status_code=400, detail="Region height must be positive")
    if region_x is not None and region_x < 0:
        raise HTTPException(status_code=400, detail="Region x must be >= 0")
    if region_y is not None and region_y < 0:
        raise HTTPException(status_code=400, detail="Region y must be >= 0")

    prompt_text = description or prompt or ""
    prompt_text += _build_region_hint(region_x, region_y, region_width, region_height)
    reference_images = []
    if references:
        for ref in references:
            reference_images.append(await ref.read())
    total_images = 1 + len(reference_images)
    model_name = config.nano_banana_model
    if model_name.startswith("gemini-2.5-flash-image"):
        model_limit = 3
    elif model_name.startswith("gemini-3-pro-image"):
        model_limit = 14
    else:
        model_limit = config.nano_banana_max_images
    max_images = max(1, min(model_limit, config.nano_banana_max_images))
    if total_images > max_images:
        raise HTTPException(
            status_code=400,
            detail=f"Too many images: {total_images} > {max_images}",
        )
    job_id = uuid.uuid4().hex
    record = store.create(job_id)
    record.status = "queued"
    record.progress = 0
    raw = await image.read()
    selected_name = file_name or image.filename
    selected_mime = mime or image.content_type
    background.add_task(
        run_image_job,
        job_id,
        raw,
        prompt_text,
        reference_images,
        selected_name,
        selected_mime,
    )
    return JobStatus(id=job_id, status=record.status, progress=record.progress)


def _format_sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=True)}\n\n"


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str) -> StreamingResponse:
    record = store.get(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_stream() -> AsyncGenerator[str, None]:
        while True:
            event = await store.next_event(job_id)
            if event is None:
                break
            yield _format_sse(event)
            if event.get("type") in {"completed", "failed"}:
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")
