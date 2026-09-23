"""Run the daily pipeline on Garmin Health summaries.

Pass --file for a webhook payload. With GARMIN_ACCESS_TOKEN, the script
asks the Health API for summaries uploaded in the requested window.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.env import read_secret
from integrations.garmin.client import fetch_history, load_payload
from integrations.garmin.normalize import garmin_to_daily
from integrations.http import ProviderError
from integrations.output import publish


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=None, help="Saved Garmin webhook JSON")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--start", type=date.fromisoformat, default=None)
    parser.add_argument("--end", type=date.fromisoformat, default=None)
    parser.add_argument("--user", default="garmin")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "processed" / "garmin")
    args = parser.parse_args()
    try:
        history = _history(args)
    except ProviderError as error:
        sys.exit(str(error))
    daily = garmin_to_daily(
        args.user,
        history["dailies"],
        history["sleeps"],
        history["hrv"],
        history["respiration"],
        history["skinTemp"],
    )
    results = publish(
        daily,
        out=args.out,
        heading="GARMIN",
        note="Stress and Body Battery were not used as measurements.",
        events_file="data/processed/garmin/events.csv",
    )
    if not results:
        sys.exit("Garmin summaries did not contain any days.")


def _history(args):
    if args.file is not None:
        if not args.file.exists():
            raise ProviderError(f"Garmin file not found at {args.file}.")
        return load_payload(args.file)
    token = read_secret(ROOT, "GARMIN_ACCESS_TOKEN")
    if not token:
        raise ProviderError(
            "Pass --file with a Garmin Health webhook payload, or set GARMIN_ACCESS_TOKEN. "
            "The Health API is granted through Garmin's developer program. Do not commit the token."
        )
    end = args.end or (date.today() - timedelta(days=1))
    start = args.start or (end - timedelta(days=max(args.days, 1) - 1))
    return fetch_history(token, start, end)


if __name__ == "__main__":
    main()
