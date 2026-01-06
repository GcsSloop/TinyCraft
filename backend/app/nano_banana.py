from __future__ import annotations

from io import BytesIO
from typing import Optional
from urllib.parse import urljoin

from PIL import Image

from .config import AppConfig


def apply_edit(
    content: bytes,
    region_start: int,
    region_end: int,
    description: str,
) -> bytes:
    """
    Stub for non-image file edits.
    Uses a simple byte-range replace to simulate modification.
    """
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return content

    if region_start < 0 or region_end < region_start or region_end > len(text):
        return content

    updated = text[:region_start] + description + text[region_end:]
    return updated.encode("utf-8")


def _build_client(api_key: str, base_url: Optional[str], timeout: Optional[int]):
    from google import genai

    options = {}
    if base_url:
        options["base_url"] = base_url
    if timeout:
        options["timeout"] = int(timeout * 1000)
    if options:
        return genai.Client(api_key=api_key, http_options=options)
    return genai.Client(api_key=api_key)


def _build_http_options(config: AppConfig) -> dict:
    options: dict = {}
    if config.nano_banana_base_url:
        options["base_url"] = config.nano_banana_base_url
    if config.nano_banana_timeout:
        options["timeout"] = int(config.nano_banana_timeout * 1000)
    client_args = {}
    if config.nano_banana_proxy:
        client_args["proxy"] = config.nano_banana_proxy
    client_args["trust_env"] = config.nano_banana_trust_env
    if client_args:
        options["client_args"] = client_args
    return options


def _normalize_modalities(raw: str) -> list[str]:
    items = [item.strip().upper() for item in raw.split(",") if item.strip()]
    if "IMAGE" not in items:
        items.append("IMAGE")
    return items or ["TEXT", "IMAGE"]


def _normalize_aspect_ratio(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = value.strip().lower()
    if cleaned in {"auto", "keep", "default"}:
        return None
    return value


def _sanitize_detail(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, dict)):
        return value
    return str(value)


def extract_error_context(exc: BaseException) -> dict:
    context: dict = {
        "exception_type": exc.__class__.__name__,
    }
    for item in _iter_causes(exc):
        for key in ("code", "status", "message", "details"):
            if key not in context and hasattr(item, key):
                context[key] = _sanitize_detail(getattr(item, key))
        response = getattr(item, "response", None)
        if response is not None:
            status_code = getattr(response, "status_code", None) or getattr(
                response, "status", None
            )
            if status_code:
                context["http_status"] = status_code
            headers = getattr(response, "headers", None)
            if headers:
                for header in (
                    "x-request-id",
                    "x-goog-request-id",
                    "x-guploader-uploadid",
                    "x-goog-trace-id",
                ):
                    if header in headers:
                        context[header] = headers.get(header)
        if context.get("http_status"):
            break
    return context

def _iter_causes(exc: BaseException):
    seen = set()
    current = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def classify_error(exc: BaseException) -> tuple[str, str]:
    for item in _iter_causes(exc):
        name = item.__class__.__name__
        if isinstance(item, ValueError) and "NANO_BANANA_API_KEY" in str(item):
            return "auth_failed", "鉴权失败：缺少 API Key"
        response = getattr(item, "response", None)
        status = getattr(response, "status_code", None)
        if status in (401, 403):
            return "auth_failed", "鉴权失败：API Key 无效或无权限"
        if status == 429:
            return "rate_limited", "请求过于频繁：请稍后重试"
        if status and status >= 500:
            return "upstream_error", f"上游服务异常：HTTP {status}"

        if name in {
            "ConnectTimeout",
            "ReadTimeout",
            "ConnectError",
            "NetworkError",
            "RemoteProtocolError",
        }:
            return "network_unreachable", "网络不可达或连接超时"

        if "_ssl.c" in str(item):
            return "network_unreachable", "TLS 握手超时或网络不可达"

    return "unknown_error", f"未知错误：{exc}"


def _health_base_url(config: AppConfig) -> str:
    return config.nano_banana_base_url or "https://generativelanguage.googleapis.com/v1beta/"


def check_connectivity(config: AppConfig) -> dict:
    if not config.nano_banana_api_key:
        return {"status": "auth_failed", "message": "鉴权失败：缺少 API Key"}

    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - dependency issue
        return {"status": "unknown_error", "message": str(exc)}

    url = urljoin(_health_base_url(config), "models")
    try:
        client_args = {
            "proxy": config.nano_banana_proxy,
            "trust_env": config.nano_banana_trust_env,
        }
        with httpx.Client(**client_args) as client:
            resp = client.get(
                url,
                params={"key": config.nano_banana_api_key},
                timeout=config.nano_banana_timeout,
            )
    except Exception as exc:  # pragma: no cover - network depends on env
        status, message = classify_error(exc)
        return {"status": status, "message": message}

    if resp.status_code in (401, 403):
        return {"status": "auth_failed", "message": "鉴权失败：API Key 无效或无权限"}
    if resp.status_code >= 400:
        return {
            "status": "upstream_error",
            "message": f"上游服务异常：HTTP {resp.status_code}",
        }
    return {"status": "ok", "message": "连接正常"}


def edit_image(
    image_bytes: bytes,
    prompt: str,
    config: AppConfig,
) -> bytes:
    if not config.nano_banana_api_key:
        raise ValueError("Missing NANO_BANANA_API_KEY")

    http_options = _build_http_options(config)
    from google import genai
    client = genai.Client(api_key=config.nano_banana_api_key, http_options=http_options)
    image = Image.open(BytesIO(image_bytes))

    from google.genai import types

    response_modalities = _normalize_modalities(
        config.nano_banana_response_modalities
    )
    if set(response_modalities) == {"TEXT", "IMAGE"}:
        response_modalities = []
    tools = [{"google_search": {}}] if config.nano_banana_enable_search else None

    image_config = {}
    aspect_ratio = _normalize_aspect_ratio(config.nano_banana_aspect_ratio)
    if aspect_ratio:
        image_config["aspect_ratio"] = aspect_ratio
    if config.nano_banana_model.startswith("gemini-3-pro-image"):
        if config.nano_banana_image_size:
            image_config["image_size"] = config.nano_banana_image_size

    config_kwargs = {}
    if response_modalities:
        config_kwargs["response_modalities"] = response_modalities
    if image_config:
        config_kwargs["image_config"] = types.ImageConfig(**image_config)
    if tools:
        config_kwargs["tools"] = tools

    if config_kwargs:
        response = client.models.generate_content(
            model=config.nano_banana_model,
            contents=[prompt, image],
            config=types.GenerateContentConfig(**config_kwargs),
        )
    else:
        response = client.models.generate_content(
            model=config.nano_banana_model,
            contents=[prompt, image],
        )

    for part in response.parts:
        if part.inline_data is not None:
            data = getattr(part.inline_data, "data", None)
            if data:
                return bytes(data)
            output = part.as_image()
            buffer = BytesIO()
            try:
                output.save(buffer, format="PNG")
            except TypeError:
                output.save(buffer)
            return buffer.getvalue()

    raise RuntimeError("No image returned from nano banana")
