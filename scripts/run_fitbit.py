"""Pull one consented Fitbit account and run the same daily pipeline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.env import read_secret
from integrations.fitbit.client import fetch_history
from integrations.fitbit.normalize import fitbit_to_daily
from integrations.http import ProviderError
from integrations.output import publish
from scripts._provider_cli import parse_window


def main() -> None:
    args = parse_window("Fitbit")
    token = read_secret(ROOT, "FITBIT_ACCESS_TOKEN")
    if not token:
        sys.exit(
            "Set FITBIT_ACCESS_TOKEN from https://dev.fitbit.com. "
            "Request heart rate, HRV, sleep, breathing rate, temperature, and activity. "
            "Do not commit the token."
        )
    try:
        history = fetch_history(token, args.start, args.end)
    except ProviderError as error:
        sys.exit(str(error))
    args.raw.mkdir(parents=True, exist_ok=True)
    (args.raw / "history.json").write_text(json.dumps(history), encoding="utf-8")
    daily = fitbit_to_daily(
        args.user,
        history["heart"],
        history["steps"],
        history["sleep"],
        history["hrv"],
        history["breathing"],
        history["skin"],
    )
    results = publish(
        daily,
        out=args.out,
        heading="FITBIT",
        note="Heart-rate zones were not used. Skin temperature is the nightly change from baseline.",
        events_file="data/processed/fitbit/events.csv",
    )
    if not results:
        sys.exit(f"Fitbit returned no days between {args.start.isoformat()} and {args.end.isoformat()}.")


if __name__ == "__main__":
    main()
