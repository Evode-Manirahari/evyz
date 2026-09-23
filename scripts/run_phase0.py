"""Run the phase-0 loop on one real WearableQA cohort."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.normalization.wearableqa import load_wearableqa
from core.pipeline import PipelineConfig, analyze_person
from core.report import choose_segment, format_segment, format_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        type=Path,
        default=ROOT / "data" / "raw" / "wearableqa" / "structured.parquet",
    )
    parser.add_argument("--user", default=None, help="Print this user id, such as user_25")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "processed")
    args = parser.parse_args()
    if not args.data.exists():
        sys.exit(f"Dataset not found at {args.data}. Run scripts/download_wearableqa.py first.")

    daily = load_wearableqa(args.data)
    config = PipelineConfig()
    results = []
    for user_id, person in daily.groupby("user_id", sort=True):
        results.extend(analyze_person(person, config))

    args.out.mkdir(parents=True, exist_ok=True)
    _write(args.out, results)
    print(format_summary(results))
    print()
    chosen = choose_segment(results, args.user)
    if chosen is None:
        sys.exit("No timelines were loaded.")
    print(format_segment(chosen))


def _write(out: Path, results) -> None:
    import pandas as pd

    quality_rows = []
    event_rows = []
    for item in results:
        quality_rows.append(
            {
                "user_id": item.user_id,
                "start_date": item.start_date.date().isoformat(),
                "end_date": item.end_date.date().isoformat(),
                "n_observed_resting_hr": item.n_observed_resting_hr,
                "usable": item.usable,
                "n_events": len(item.events),
                "reasons": "; ".join(item.reasons),
            }
        )
        event_rows.extend(event.as_row() for event in item.events)
    pd.DataFrame(quality_rows).to_csv(out / "timelines.csv", index=False)
    pd.DataFrame(event_rows).to_csv(out / "events.csv", index=False)
    summary = format_summary(results)
    (out / "phase0_summary.txt").write_text(summary + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
