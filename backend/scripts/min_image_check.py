from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from PIL import Image

from app.config import load_config
from app.nano_banana import classify_error, extract_error_context


def build_client(config):
    from google import genai

    http_options = {}
    if config.nano_banana_base_url:
        http_options["base_url"] = config.nano_banana_base_url
    if config.nano_banana_timeout:
        http_options["timeout"] = int(config.nano_banana_timeout * 1000)
    client_args = {}
    if config.nano_banana_proxy:
        client_args["proxy"] = config.nano_banana_proxy
    client_args["trust_env"] = config.nano_banana_trust_env
    if client_args:
        http_options["client_args"] = client_args
    if http_options:
        return genai.Client(api_key=config.nano_banana_api_key, http_options=http_options)
    return genai.Client(api_key=config.nano_banana_api_key)


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal image edit check.")
    parser.add_argument("--image", required=True, help="Path to input image")
    parser.add_argument("--prompt", required=True, help="Edit prompt")
    parser.add_argument(
        "--model",
        default=None,
        help="Override model, e.g. gemini-2.5-flash-image",
    )
    parser.add_argument("--out", default="result.png", help="Output image path")
    args = parser.parse_args()

    config = load_config()
    model = args.model or config.nano_banana_model
    if not config.nano_banana_api_key:
        print("Missing API key (NANO_BANANA_API_KEY)")
        return 1

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        return 1

    image = Image.open(image_path)
    client = build_client(config)

    try:
        response = client.models.generate_content(
            model=model,
            contents=[args.prompt, image],
        )
    except Exception as exc:
        kind, message = classify_error(exc)
        print(f"[{kind}] {message}")
        print(extract_error_context(exc))
        return 2

    saved = False
    for part in response.parts:
        if part.inline_data is not None:
            output = part.as_image()
            output.save(args.out)
            print(f"Saved: {args.out}")
            saved = True
        elif part.text:
            print(part.text)
    if not saved:
        print("No image returned.")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
