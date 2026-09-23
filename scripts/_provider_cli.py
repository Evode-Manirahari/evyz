"""Shared date window for a live provider script."""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_window(provider: str):
    parser = argparse.ArgumentParser(description=f"Pull one consented {provider} account.")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--start", type=date.fromisoformat, default=None)
    parser.add_argument("--end", type=date.fromisoformat, default=None)
    parser.add_argument("--user", default=provider.lower())
    slug = provider.lower()
    parser.add_argument("--raw", type=Path, default=ROOT / "data" / "raw" / slug)
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "processed" / slug)
    args = parser.parse_args()
    args.end = args.end or (date.today() - timedelta(days=1))
    args.start = args.start or (args.end - timedelta(days=max(args.days, 1) - 1))
    if args.end < args.start:
        sys.exit("The end date is before the start date.")
    return args
