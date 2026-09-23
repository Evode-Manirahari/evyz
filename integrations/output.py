"""Write one provider run in the same shape as the phase-0 report."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.pipeline import PipelineConfig, SegmentResult, analyze_person
from core.report import format_segment, format_summary
from core.status import latest_segment


def publish(
    daily: pd.DataFrame,
    *,
    out: Path,
    heading: str,
    note: str,
    events_file: str,
) -> list[SegmentResult]:
    results = analyze_person(daily, PipelineConfig()) if not daily.empty else []
    out.mkdir(parents=True, exist_ok=True)
    daily.to_csv(out / "daily.csv", index=False)
    rows = [event.as_row() for item in results for event in item.events]
    pd.DataFrame(rows).to_csv(out / "events.csv", index=False)
    summary = format_summary(results, heading=heading, note=note)
    (out / "summary.txt").write_text(summary + "\n", encoding="utf-8")
    print(summary)
    print()
    chosen = latest_segment(results)
    if chosen is not None:
        print(format_segment(chosen, events_file=events_file))
    return results
