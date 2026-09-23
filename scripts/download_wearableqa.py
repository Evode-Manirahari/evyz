"""Download the WearableQA structured split used by phase 0."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://huggingface.co/datasets/facebook/WearableQA/resolve/main/data/structured/test-00000-of-00001.parquet"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dest",
        type=Path,
        default=ROOT / "data" / "raw" / "wearableqa" / "structured.parquet",
    )
    args = parser.parse_args()
    if args.dest.exists() and args.dest.stat().st_size > 0:
        print(f"Dataset already present at {args.dest}")
        return
    args.dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {URL}")
    subprocess.run(["curl", "-fL", "--retry", "3", "-o", str(args.dest), URL], check=True)
    print(f"Saved {args.dest}")
    print("License: CC BY-NC 4.0. Keep this file local. Do not ship it in the product.")


if __name__ == "__main__":
    main()
