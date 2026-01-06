from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PIL import Image
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.nano_banana import classify_error, extract_error_context


def _print_error(exc: BaseException) -> None:
    kind, message = classify_error(exc)
    print(f"[{kind}] {message}")
    print(extract_error_context(exc))


def main() -> int:
    parser = argparse.ArgumentParser(description="GenAI image diagnose script.")
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash-image",
        help="Model name, e.g. gemini-2.5-flash-image",
    )
    parser.add_argument(
        "--prompt",
        default="Create a simple red circle on a white background.",
        help="Prompt text",
    )
    parser.add_argument(
        "--image",
        default=None,
        help="Optional image path to test image+text request",
    )
    parser.add_argument(
        "--out",
        default="diagnose_result.png",
        help="Output path for image response",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("NANO_BANANA_API_KEY")
    if not api_key:
        print("Missing NANO_BANANA_API_KEY")
        return 1

    from google import genai

    client = genai.Client(api_key=api_key)

    print("Step 1) List image-capable models")
    try:
        models = [m.name for m in client.models.list() if "image" in m.name]
        print(f"image models: {models}")
    except Exception as exc:
        _print_error(exc)
        return 2

    print("Step 2) Text-only request")
    try:
        response = client.models.generate_content(
            model=args.model,
            contents=[args.prompt],
        )
        text_parts = [p.text for p in response.parts if p.text]
        if text_parts:
            print("text-only response:", text_parts[0][:200])
        else:
            print("text-only ok (no text parts)")
    except Exception as exc:
        _print_error(exc)
        return 3

    if not args.image:
        print("Step 3) Skipped (no image provided)")
        return 0

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        return 4

    image = Image.open(image_path)
    print(f"Step 3) Image+text request (size={image.size}, mode={image.mode})")
    try:
        response = client.models.generate_content(
            model=args.model,
            contents=[args.prompt, image],
        )
        saved = False
        for part in response.parts:
            if part.inline_data is not None:
                output = part.as_image()
                output.save(args.out)
                print(f"Saved: {args.out}")
                saved = True
                break
        if not saved:
            print("No image returned.")
    except Exception as exc:
        _print_error(exc)
        return 5

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
