"""Rolling personal normal range.

The current day is excluded. A change cannot define the baseline it is
compared against. Windows are calendar days inside one contiguous segment,
so a long gap does not get treated as recent history.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.schema import DAILY_METRICS, MAD_FLOOR


def add_baselines(
    segment: pd.DataFrame,
    *,
    window: int,
    min_periods: int,
) -> pd.DataFrame:
    frame = segment.copy()
    for metric in DAILY_METRICS:
        if metric not in frame.columns:
            frame[metric] = np.nan
        history = pd.to_numeric(frame[metric], errors="coerce").shift(1)
        rolled = history.rolling(window=window, min_periods=min_periods)
        frame[f"{metric}_baseline"] = rolled.median()
        frame[f"{metric}_p10"] = rolled.quantile(0.10)
        frame[f"{metric}_p90"] = rolled.quantile(0.90)
        frame[f"{metric}_mad"] = history.rolling(window=window, min_periods=min_periods).apply(
            _mad, raw=True
        )
        frame[f"{metric}_baseline_days"] = history.rolling(window=window, min_periods=1).count()
    return frame


def split_segments(daily: pd.DataFrame, *, max_gap_days: int) -> list[pd.DataFrame]:
    """Split one person's days wherever the calendar gap is too long."""
    frame = daily.sort_values("date").copy()
    frame["date"] = pd.to_datetime(frame["date"])
    if frame.empty:
        return []
    gaps = frame["date"].diff().dt.days.fillna(1)
    segment_id = (gaps > max_gap_days).cumsum()
    segments = []
    for _, part in frame.groupby(segment_id, sort=True):
        segments.append(_daily_grid(part.reset_index(drop=True)))
    return segments


def _daily_grid(segment: pd.DataFrame) -> pd.DataFrame:
    segment = segment.copy()
    segment["date"] = pd.to_datetime(segment["date"])
    segment = segment.set_index("date").sort_index()
    # A repeated date should already have been removed. Keep the first.
    segment = segment[~segment.index.duplicated(keep="first")]
    full_index = pd.date_range(segment.index.min(), segment.index.max(), freq="D")
    gridded = segment.reindex(full_index)
    gridded.index.name = "date"
    gridded = gridded.reset_index()
    if "user_id" in segment.columns and segment["user_id"].notna().any():
        gridded["user_id"] = segment["user_id"].dropna().iloc[0]
    if "source" in segment.columns and segment["source"].notna().any():
        gridded["source"] = segment["source"].dropna().iloc[0]
    return gridded


def _mad(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return np.nan
    center = np.median(finite)
    return float(np.median(np.abs(finite - center)))


def robust_z(value: float, baseline: float, mad: float, metric: str) -> float:
    if not np.isfinite(value) or not np.isfinite(baseline) or not np.isfinite(mad):
        return np.nan
    scale = 1.4826 * max(float(mad), MAD_FLOOR[metric])
    return (float(value) - float(baseline)) / scale
