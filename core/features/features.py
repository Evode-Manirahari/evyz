"""Express each day relative to the personal baseline."""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.baseline.baseline import robust_z
from core.schema import DAILY_METRICS, PERCENT_FLOOR


def add_personalized_features(segment: pd.DataFrame) -> pd.DataFrame:
    frame = segment.copy()
    for metric in DAILY_METRICS:
        values = pd.to_numeric(frame[metric], errors="coerce")
        baseline = pd.to_numeric(frame[f"{metric}_baseline"], errors="coerce")
        mad = pd.to_numeric(frame[f"{metric}_mad"], errors="coerce")
        frame[f"{metric}_diff"] = values - baseline
        frame[f"{metric}_pct"] = [
            _percent(value, center, metric)
            for value, center in zip(values, baseline)
        ]
        frame[f"{metric}_robust_z"] = [
            robust_z(value, center, scale, metric)
            for value, center, scale in zip(values, baseline, mad)
        ]
        frame[f"{metric}_slope"] = _three_day_slope(frame["date"], values)
    return frame


def _percent(value: float, baseline: float, metric: str) -> float:
    if not np.isfinite(value) or not np.isfinite(baseline):
        return np.nan
    if abs(baseline) < PERCENT_FLOOR[metric]:
        return np.nan
    return (value - baseline) / abs(baseline) * 100.0


def _three_day_slope(dates: pd.Series, values: pd.Series) -> pd.Series:
    """Change per day from two days ago to today, when those days exist."""
    slopes = np.full(len(values), np.nan)
    date_values = pd.to_datetime(dates)
    array = values.to_numpy(dtype=float)
    for index in range(2, len(array)):
        span = (date_values.iloc[index] - date_values.iloc[index - 2]).days
        window = array[index - 2 : index + 1]
        if span == 2 and np.isfinite(window).all():
            slopes[index] = (window[-1] - window[0]) / 2.0
    return pd.Series(slopes, index=values.index)
