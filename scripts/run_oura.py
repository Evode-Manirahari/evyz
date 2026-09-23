"""Pull one consented Oura account and run the same daily pipeline."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pipeline import PipelineConfig, analyze_person
from core.report import format_segment, format_summary
from integrations.oura.client import OuraError, fetch_history
from integrations.oura.normalize import oura_to_daily


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=90, help="How many days to request, ending yesterday")
    parser.add_argument("--start", type=date.fromisoformat, default=None)
    parser.add_argument("--end", type=date.fromisoformat, default=None)
    parser.add_argument("--user", default="oura", help="Local id for this account. Not an email.")
    parser.add_argument("--raw", type=Path, default=ROOT / "data" / "raw" / "oura")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "processed" / "oura")
    args = parser.parse_args()
    end = args.end or (date.today() - timedelta(days=1))
    start = args.start or (end - timedelta(days=max(args.days, 1) - 1))
    token = _token()

    try:
        history = fetch_history(token, start, end)
    except OuraError as error:
        sys.exit(str(error))

    args.raw.mkdir(parents=True, exist_ok=True)
    for name in ("sleep", "activity", "readiness"):
        (args.raw / f"{name}.json").write_text(
            json.dumps(history[name], indent=2),
            encoding="utf-8",
        )
    daily = oura_to_daily(args.user, history["sleep"], history["activity"], history["readiness"])
    results = analyze_person(daily, PipelineConfig()) if not daily.empty else []
    args.out.mkdir(parents=True, exist_ok=True)
    daily.to_csv(args.out / "daily.csv", index=False)
    event_rows = [event.as_row() for item in results for event in item.events]
    _write_events(args.out / "events.csv", event_rows)
    summary = format_summary(
        results,
        heading="OURA",
        note="One consented Oura account. Contributor scores were not used as measurements.",
    )
    (args.out / "summary.txt").write_text(summary + "\n", encoding="utf-8")
    print(summary)
    print()
    if not results:
        sys.exit(
            f"Oura returned no days between {start.isoformat()} and {end.isoformat()}. "
            "Check that the token includes the daily scope."
        )
    print(format_segment(results[0], events_file="data/processed/oura/events.csv"))


def _token() -> str:
    value = os.environ.get("OURA_ACCESS_TOKEN", "").strip()
    if value:
        return value
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, raw = stripped.split("=", 1)
            if key.strip() == "OURA_ACCESS_TOKEN":
                found = raw.strip().strip('"').strip("'")
                if found:
                    return found
    sys.exit(
        "Set OURA_ACCESS_TOKEN. Create a personal access token with only the daily "
        "scope at https://cloud.ouraring.com/personal-access-tokens and put it in .env. "
        "Do not commit that file."
    )


def _write_events(path: Path, rows: list[dict]) -> None:
    import pandas as pd

    pd.DataFrame(rows).to_csv(path, index=False)


if __name__ == "__main__":
    main()
