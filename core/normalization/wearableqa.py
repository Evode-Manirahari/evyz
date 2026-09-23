"""Load WearableQA daily histories into the canonical schema.

Question text, blood panels, and answer keys are ignored. They are not
measurements, and they are not labels for EVYZ events.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from core.schema import DAILY_COLUMNS, DAILY_METRICS, SOURCE_WEARABLEQA

_ALIASES = {
    "resting_hr": ("rhr", "resting_hr", "resting_heart_rate"),
    "hrv": ("hrv", "hrv_rmssd", "heart_rate_variability"),
    "steps": ("steps", "step_count"),
    "respiratory_rate": ("respiratory_rate", "respiration", "resp", "rr"),
    "skin_temperature_delta": ("skin_temperature_delta", "temp_delta", "temperature_delta"),
}

_SLEEP_KEYS = (
    "sleep_minutes",
    "sleep_min",
    "sleep_duration",
    "sleep",
    "sleep_hours",
    "sleep_h",
    "sleeph",
    "slph",
    "sldur",
    "slp",
)


def load_wearableqa(path: Path) -> pd.DataFrame:
    table = pd.read_parquet(path, columns=["id", "sensor_history"])
    rows: list[dict] = []
    keys_seen: set[str] = set()
    for user_id, record in _one_history_per_person(table):
        for day in _history_days(record.get("sensor_history")):
            keys_seen.update(str(key) for key in day.keys())
            mapped = _map_day(day)
            mapped["user_id"] = user_id
            mapped["source"] = SOURCE_WEARABLEQA
            rows.append(mapped)
    if not rows:
        raise ValueError(f"No daily histories found in {path}")
    daily = pd.DataFrame(rows)
    daily["date"] = pd.to_datetime(daily["date"], errors="coerce")
    daily = daily.dropna(subset=["date"])
    daily["sleep_minutes"] = _coerce_sleep(daily["sleep_minutes"], daily.pop("sleep_was_minutes"))
    for metric in DAILY_METRICS:
        daily[metric] = pd.to_numeric(daily[metric], errors="coerce")
    aggregated = daily.groupby(["user_id", "date"], as_index=False)[list(DAILY_METRICS)].median()
    aggregated["source"] = SOURCE_WEARABLEQA
    aggregated = aggregated[list(DAILY_COLUMNS)]
    if aggregated["resting_hr"].notna().sum() == 0:
        found = ", ".join(sorted(keys_seen))
        raise ValueError(f"Resting heart rate was not found. Day keys were: {found}")
    return aggregated


def days_to_frame(user_id: str, days: list[dict], *, source: str = SOURCE_WEARABLEQA) -> pd.DataFrame:
    """Map already-parsed days. Used by tests and by the file loader."""
    rows = []
    for day in days:
        mapped = _map_day(day)
        mapped["user_id"] = user_id
        mapped["source"] = source
        rows.append(mapped)
    frame = pd.DataFrame(rows)
    frame["sleep_minutes"] = _coerce_sleep(frame["sleep_minutes"], frame.pop("sleep_was_minutes"))
    frame["source"] = source
    return frame[list(DAILY_COLUMNS)]


def _map_day(day: dict) -> dict:
    lowered = {str(key).lower(): value for key, value in day.items()}
    mapped = {metric: _first(lowered, keys) for metric, keys in _ALIASES.items()}
    sleep_value, sleep_key = _sleep_value(lowered)
    mapped["sleep_minutes"] = sleep_value
    mapped["sleep_was_minutes"] = sleep_key in ("sleep_minutes", "sleep_min")
    mapped["date"] = lowered.get("date")
    return mapped


def _sleep_value(lowered: dict) -> tuple[float | None, str | None]:
    for key in _SLEEP_KEYS:
        if key in lowered and _finite(lowered[key]):
            return float(lowered[key]), key
    return None, None


def _coerce_sleep(values: pd.Series, already_minutes: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    minutes = already_minutes.reindex(numeric.index).fillna(False).astype(bool)
    hour_values = numeric.loc[~minutes]
    treat_as_hours = True
    finite = hour_values[np.isfinite(hour_values)]
    if len(finite) and float(np.median(finite)) > 24:
        treat_as_hours = False
    converted = numeric.copy()
    if treat_as_hours:
        converted.loc[~minutes] = numeric.loc[~minutes] * 60.0
    return converted


def _first(lowered: dict, keys: tuple[str, ...]) -> float | None:
    for key in keys:
        if key in lowered and _finite(lowered[key]):
            return float(lowered[key])
    return None


def _finite(value) -> bool:
    if value is None or value is pd.NA:
        return False
    try:
        if pd.isna(value):
            return False
    except TypeError:
        return False
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def _one_history_per_person(table: pd.DataFrame) -> list[tuple[str, dict]]:
    """Keep the longest daily history for each person.

    The file repeats a person's history once per benchmark question.
    """
    best: dict[str, tuple[int, dict]] = {}
    for record in table.to_dict(orient="records"):
        user_id = _user_id(record)
        length = len(record["sensor_history"]) if record.get("sensor_history") is not None else 0
        current = best.get(user_id)
        if current is None or length > current[0]:
            best[user_id] = (length, record)
    return [(user_id, record) for user_id, (_length, record) in best.items()]


def _user_id(record: dict) -> str:
    if record.get("user_id"):
        return str(record["user_id"])
    match = re.search(r"user_(\d+)", str(record.get("id", "")))
    if not match:
        raise ValueError(f"Could not find a user id in record {record.get('id')!r}")
    return f"user_{match.group(1)}"


def _history_days(history) -> list[dict]:
    if history is None:
        return []
    if hasattr(history, "tolist"):
        history = history.tolist()
    days = []
    for item in history:
        if hasattr(item, "tolist") and not isinstance(item, dict):
            item = item.tolist()
        if not isinstance(item, dict):
            item = dict(item)
        days.append(item)
    return days
