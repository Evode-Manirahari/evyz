"""Label each day as normal, unusual, or a strong deviation.

Days inside the baseline window are not flagged. Missing values stay missing.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from core.schema import DAILY_METRICS


def add_deviation_labels(
    segment: pd.DataFrame,
    *,
    unusual_z: float,
    strong_z: float,
    min_baseline_days: int,
) -> pd.DataFrame:
    frame = segment.copy()
    for metric in DAILY_METRICS:
        levels = []
        changed = []
        strong = []
        z_values = frame[f"{metric}_robust_z"]
        history = frame[f"{metric}_baseline_days"]
        for z_value, days in zip(z_values, history):
            if not np.isfinite(days) or days < min_baseline_days or not np.isfinite(z_value):
                levels.append("missing")
                changed.append(False)
                strong.append(False)
                continue
            magnitude = abs(float(z_value))
            if magnitude >= strong_z:
                levels.append("strong")
                changed.append(True)
                strong.append(True)
            elif magnitude >= unusual_z:
                levels.append("unusual")
                changed.append(True)
                strong.append(False)
            else:
                levels.append("normal")
                changed.append(False)
                strong.append(False)
        frame[f"{metric}_level"] = levels
        frame[f"{metric}_changed"] = changed
        frame[f"{metric}_strong"] = strong
        frame[f"{metric}_consecutive"] = _consecutive(frame["date"], changed)
    changed_columns = [f"{metric}_changed" for metric in DAILY_METRICS]
    strong_columns = [f"{metric}_strong" for metric in DAILY_METRICS]
    frame["n_changed"] = frame[changed_columns].sum(axis=1).astype(int)
    frame["n_strong"] = frame[strong_columns].sum(axis=1).astype(int)
    return frame


def _consecutive(dates: pd.Series, changed: list[bool]) -> list[int]:
    counts = []
    run = 0
    previous = None
    for day, flag in zip(pd.to_datetime(dates), changed):
        if previous is not None and (day - previous).days != 1:
            run = 0
        run = run + 1 if flag else 0
        counts.append(run)
        previous = day
    return counts
