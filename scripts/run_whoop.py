"""Pull one consented WHOOP account and run the same daily pipeline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.env import read_secret
from integrations.http import ProviderError
from integrations.output import publish
from integrations.whoop.client import fetch_history
from integrations.whoop.normalize import whoop_to_daily
from scripts._provider_cli import parse_window


def main() -> None:
    args = parse_window("WHOOP")
    token = read_secret(ROOT, "WHOOP_ACCESS_TOKEN")
    if not token:
        sys.exit(
            "Set WHOOP_ACCESS_TOKEN. Create an app at https://developer.whoop.com "
            "and authorize read:recovery and read:sleep only. Do not commit the token."
        )
    try:
        history = fetch_history(token, args.start, args.end)
    except ProviderError as error:
        sys.exit(str(error))
    args.raw.mkdir(parents=True, exist_ok=True)
    for name in ("recovery", "sleep"):
        (args.raw / f"{name}.json").write_text(json.dumps(history[name]), encoding="utf-8")
    daily = whoop_to_daily(args.user, history["recovery"], history["sleep"])
    results = publish(
        daily,
        out=args.out,
        heading="WHOOP",
        note="Recovery score and absolute skin temperature were not used as measurements.",
        events_file="data/processed/whoop/events.csv",
    )
    if not results:
        sys.exit(f"WHOOP returned no days between {args.start.isoformat()} and {args.end.isoformat()}.")


if __name__ == "__main__":
    main()
