"""Turn unusable measurements into missing values.

A missing day is not a zero, and it is not an event.
"""

from __future__ import annotations

import pandas as pd

from core.schema import DAILY_METRICS, PLAUSIBLE


def apply_quality(daily: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    frame = daily.copy()
    removed: dict[str, int] = {}
    for metric in DAILY_METRICS:
        if metric not in frame.columns:
            frame[metric] = pd.NA
            continue
        values = pd.to_numeric(frame[metric], errors="coerce")
        low, high = PLAUSIBLE[metric]
        invalid = values.notna() & ~values.between(low, high)
        removed[metric] = int(invalid.sum())
        values = values.mask(invalid)
        frame[metric] = values
    frame["date"] = pd.to_datetime(frame["date"]).dt.tz_localize(None)
    frame = frame.drop_duplicates(subset=["user_id", "date"], keep="first")
    return frame.sort_values(["user_id", "date"]).reset_index(drop=True), removed
