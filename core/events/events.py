"""Group persistent deviations into events.

An event is created when either:

- two or more signals are outside the personal range on the same days, for
  at least `min_days`, or
- one signal is a strong deviation for at least `min_days`.

A single unusual day is not an event.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from core.schema import DAILY_METRICS, UNITS


@dataclass
class ChangeEvent:
    user_id: str
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    duration_days: int
    status: str
    rule: str
    signals: list[str]
    metrics: dict[str, dict] = field(default_factory=dict)
    recovery_days: int | None = None
    explanation: str = ""

    def as_row(self) -> dict:
        return {
            "user_id": self.user_id,
            "start_date": self.start_date.date().isoformat(),
            "end_date": self.end_date.date().isoformat(),
            "duration_days": self.duration_days,
            "status": self.status,
            "rule": self.rule,
            "n_signals": len(self.signals),
            "signals": "|".join(self.signals),
            "recovery_days": self.recovery_days,
            "explanation": self.explanation,
            **{
                f"{metric}_percent": self.metrics.get(metric, {}).get("percent")
                for metric in DAILY_METRICS
            },
        }


def build_events(segment: pd.DataFrame, *, min_days: int, unusual_z: float) -> list[ChangeEvent]:
    if segment.empty:
        return []
    frame = segment.reset_index(drop=True)
    multi_runs = _true_runs(frame["n_changed"].ge(2).to_numpy())
    events = [_event_from_run(frame, start, end, "multi_signal", unusual_z) for start, end in multi_runs if end - start + 1 >= min_days]
    covered = _covered_days(events, frame)
    for metric in DAILY_METRICS:
        strong_runs = _true_runs(frame[f"{metric}_strong"].to_numpy(dtype=bool))
        for start, end in strong_runs:
            for piece_start, piece_end in _uncovered_runs(start, end, covered, min_days):
                single = _event_from_run(
                    frame, piece_start, piece_end, "strong_single", unusual_z, only_metric=metric
                )
                events.append(single)
                covered.update(range(piece_start, piece_end + 1))
    events.sort(key=lambda event: event.start_date)
    return events


def _event_from_run(
    frame: pd.DataFrame,
    start: int,
    end: int,
    rule: str,
    unusual_z: float,
    only_metric: str | None = None,
) -> ChangeEvent:
    block = frame.iloc[start : end + 1]
    if only_metric:
        signals = [only_metric]
    else:
        signals = _persistent_signals(block)
    user_id = str(block["user_id"].iloc[0])
    start_date = pd.Timestamp(block["date"].iloc[0])
    end_date = pd.Timestamp(block["date"].iloc[-1])
    reaches_end = end == len(frame) - 1
    return ChangeEvent(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        duration_days=int((end_date - start_date).days) + 1,
        status="ongoing" if reaches_end else "completed",
        rule=rule,
        signals=signals,
        metrics=_summaries(block, signals),
        recovery_days=None if reaches_end else _recovery_days(frame, end, signals, unusual_z),
    )


def _persistent_signals(block: pd.DataFrame) -> list[str]:
    selected = []
    for metric in DAILY_METRICS:
        if float(block[f"{metric}_changed"].mean()) >= 0.5:
            selected.append(metric)
    if len(selected) >= 2:
        return selected
    # The day rule already required two signals. Keep the two that moved most often.
    ranked = sorted(DAILY_METRICS, key=lambda metric: float(block[f"{metric}_changed"].mean()), reverse=True)
    return [metric for metric in ranked if float(block[f"{metric}_changed"].mean()) > 0][:2]


def _summaries(block: pd.DataFrame, signals: list[str]) -> dict[str, dict]:
    summaries = {}
    for metric in signals:
        baseline = float(block[f"{metric}_baseline"].median())
        during = float(pd.to_numeric(block[metric], errors="coerce").median())
        percent = pd.to_numeric(block[f"{metric}_pct"], errors="coerce").median()
        low = float(block[f"{metric}_p10"].median())
        high = float(block[f"{metric}_p90"].median())
        if during > baseline:
            direction = "above"
        elif during < baseline:
            direction = "below"
        else:
            direction = "unchanged"
        summaries[metric] = {
            "baseline": baseline,
            "during": during,
            "percent": None if pd.isna(percent) else float(percent),
            "direction": direction,
            "p10": low,
            "p90": high,
            "unit": UNITS[metric],
        }
    return summaries


def _recovery_days(frame: pd.DataFrame, end: int, signals: list[str], unusual_z: float) -> int | None:
    for offset, index in enumerate(range(end + 1, len(frame)), start=1):
        row = frame.iloc[index]
        settled = True
        for metric in signals:
            z_value = row[f"{metric}_robust_z"]
            if not np.isfinite(z_value) or abs(float(z_value)) >= unusual_z:
                settled = False
                break
        if settled:
            return offset
    return None


def _uncovered_runs(start: int, end: int, covered: set[int], min_days: int) -> list[tuple[int, int]]:
    """Keep only the stretches that are not already inside an event."""
    runs = []
    run_start = None
    for index in range(start, end + 1):
        if index in covered:
            if run_start is not None and index - run_start >= min_days:
                runs.append((run_start, index - 1))
            run_start = None
            continue
        if run_start is None:
            run_start = index
    if run_start is not None and end - run_start + 1 >= min_days:
        runs.append((run_start, end))
    return runs


def _true_runs(mask: np.ndarray) -> list[tuple[int, int]]:
    runs = []
    start = None
    values = list(mask) + [False]
    for index, flag in enumerate(values):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            runs.append((start, index - 1))
            start = None
    return runs


def _covered_days(events: list[ChangeEvent], frame: pd.DataFrame) -> set[int]:
    covered: set[int] = set()
    dates = pd.to_datetime(frame["date"])
    for event in events:
        matches = dates[(dates >= event.start_date) & (dates <= event.end_date)].index
        covered.update(int(index) for index in matches)
    return covered
