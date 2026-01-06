from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.config import load_config
from app.nano_banana import check_connectivity


def main() -> None:
    result = check_connectivity(load_config())
    status = result.get("status")
    message = result.get("message", "")
    print(f"[{status}] {message}")


if __name__ == "__main__":
    main()
