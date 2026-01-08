from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "backend" / "config" / "app.yaml"


@dataclass
class AppConfig:
    nano_banana_api_key: Optional[str] = None
    nano_banana_model: str = "gemini-3-pro-image-preview"
    nano_banana_base_url: Optional[str] = None
    nano_banana_timeout: int = 60
    nano_banana_max_images: int = 14
    nano_banana_aspect_ratio: str = "auto"
    nano_banana_image_size: str = "1K"
    nano_banana_response_modalities: str = "TEXT,IMAGE"
    nano_banana_enable_search: bool = False
    nano_banana_proxy: Optional[str] = None
    nano_banana_trust_env: bool = True

    def public_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data.pop("nano_banana_api_key", None)
        return data


def _coerce_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_file_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _load_env_config() -> Dict[str, Any]:
    load_dotenv(ROOT_DIR / "backend" / ".env")
    return {
        "nano_banana_api_key": os.getenv("NANO_BANANA_API_KEY"),
        "nano_banana_model": os.getenv("NANO_BANANA_MODEL"),
        "nano_banana_base_url": os.getenv("NANO_BANANA_BASE_URL"),
        "nano_banana_timeout": os.getenv("NANO_BANANA_TIMEOUT"),
        "nano_banana_max_images": os.getenv("NANO_BANANA_MAX_IMAGES"),
        "nano_banana_aspect_ratio": os.getenv("NANO_BANANA_ASPECT_RATIO"),
        "nano_banana_image_size": os.getenv("NANO_BANANA_IMAGE_SIZE"),
        "nano_banana_response_modalities": os.getenv("NANO_BANANA_RESPONSE_MODALITIES"),
        "nano_banana_enable_search": os.getenv("NANO_BANANA_ENABLE_SEARCH"),
        "nano_banana_proxy": os.getenv("NANO_BANANA_PROXY"),
        "nano_banana_trust_env": os.getenv("NANO_BANANA_TRUST_ENV"),
    }


def _apply_overrides(base: AppConfig, overrides: Dict[str, Any]) -> AppConfig:
    for key, value in overrides.items():
        if value is None:
            continue
        if not hasattr(base, key):
            continue
        if key in {"nano_banana_timeout", "nano_banana_max_images"}:
            try:
                setattr(base, key, int(value))
            except (TypeError, ValueError):
                continue
        elif key in {"nano_banana_enable_search", "nano_banana_trust_env"}:
            if isinstance(value, str):
                coerced = _coerce_bool(value)
                if coerced is None:
                    continue
                setattr(base, key, coerced)
            else:
                setattr(base, key, bool(value))
        else:
            setattr(base, key, value)
    return base


def load_config() -> AppConfig:
    base = AppConfig()
    file_config = _load_file_config()
    env_config = _load_env_config()
    base = _apply_overrides(base, file_config)
    env_config["nano_banana_enable_search"] = _coerce_bool(
        env_config.get("nano_banana_enable_search")
    )
    env_config["nano_banana_trust_env"] = _coerce_bool(
        env_config.get("nano_banana_trust_env")
    )
    base = _apply_overrides(base, env_config)
    return base


def save_config(payload: Dict[str, Any]) -> AppConfig:
    current = load_config()
    updated = _apply_overrides(current, payload)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = updated.public_dict()
    with CONFIG_PATH.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=False)
    return updated
