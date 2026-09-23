"""Build the canonical daily table from one provider's per-day values."""

from __future__ import annotations

import pandas as pd

from core.schema import DAILY_COLUMNS, DAILY_METRICS


def canonical_frame(user_id: str, source: str, by_day: dict[str, dict]) -> pd.DataFrame:
    if not by_day:
        return pd.DataFrame(columns=list(DAILY_COLUMNS))
    rows = []
    for day in sorted(by_day):
        values = by_day[day]
        row = {metric: values.get(metric) for metric in DAILY_METRICS}
        row["user_id"] = user_id
        row["date"] = day
        row["source"] = source
        rows.append(row)
    frame = pd.DataFrame(rows)
    frame["date"] = pd.to_datetime(frame["date"])
    for metric in DAILY_METRICS:
        frame[metric] = pd.to_numeric(frame[metric], errors="coerce")
    return frame[list(DAILY_COLUMNS)]
