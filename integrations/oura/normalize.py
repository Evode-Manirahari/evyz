"""Translate Oura documents into the canonical daily schema.

Field names follow the Oura Cloud API v2 models. Readiness contributor
scores are 1–100 ratings, so they are never copied into resting heart rate
or heart-rate variability.
"""

from __future__ import annotations

from collections import defaultdict

import pandas as pd

from core.schema import DAILY_COLUMNS, DAILY_METRICS, SOURCE_OURA


def oura_to_daily(
    user_id: str,
    sleep: list[dict],
    activity: list[dict],
    readiness: list[dict],
) -> pd.DataFrame:
    sleep_by_day: dict[str, list[dict]] = defaultdict(list)
    for document in sleep:
        day = _day(document)
        if day:
            sleep_by_day[day].append(document)
    activity_by_day = _one_per_day(activity)
    readiness_by_day = _one_per_day(readiness)
    days = sorted(set(sleep_by_day) | set(activity_by_day) | set(readiness_by_day))
    rows = []
    for day in days:
        primary = _primary_sleep(sleep_by_day.get(day, []))
        readiness_doc = readiness_by_day.get(day)
        row = {metric: pd.NA for metric in DAILY_METRICS}
        if primary is not None:
            row["resting_hr"] = primary.get("lowest_heart_rate")
            row["hrv"] = primary.get("average_hrv")
            row["sleep_minutes"] = _sleep_minutes(primary.get("total_sleep_duration"))
            row["respiratory_rate"] = primary.get("average_breath")
        activity_doc = activity_by_day.get(day)
        if activity_doc is not None:
            row["steps"] = activity_doc.get("steps")
        row["skin_temperature_delta"] = _temperature_delta(readiness_doc, primary)
        row["user_id"] = user_id
        row["date"] = day
        row["source"] = SOURCE_OURA
        rows.append(row)
    if not rows:
        return pd.DataFrame(columns=list(DAILY_COLUMNS))
    frame = pd.DataFrame(rows)
    frame["date"] = pd.to_datetime(frame["date"])
    for metric in DAILY_METRICS:
        frame[metric] = pd.to_numeric(frame[metric], errors="coerce")
    return frame[list(DAILY_COLUMNS)]


def _primary_sleep(documents: list[dict]) -> dict | None:
    """Prefer the main night. A nap on the same date must not replace it."""
    if not documents:
        return None
    long_sleeps = [document for document in documents if document.get("type") == "long_sleep"]
    pool = long_sleeps or documents
    return max(pool, key=lambda document: _seconds(document.get("total_sleep_duration")))


def _temperature_delta(readiness: dict | None, sleep: dict | None):
    if readiness is not None and readiness.get("temperature_deviation") is not None:
        return readiness.get("temperature_deviation")
    nested = (sleep or {}).get("readiness") or {}
    return nested.get("temperature_deviation")


def _one_per_day(documents: list[dict]) -> dict[str, dict]:
    chosen: dict[str, dict] = {}
    for document in documents:
        day = _day(document)
        if not day:
            continue
        current = chosen.get(day)
        if current is None or str(document.get("timestamp") or "") >= str(current.get("timestamp") or ""):
            chosen[day] = document
    return chosen


def _day(document: dict) -> str:
    raw = document.get("day")
    if raw is None:
        return ""
    return str(raw)[:10]


def _seconds(value) -> float:
    if value is None:
        return -1.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return -1.0


def _sleep_minutes(total_sleep_duration):
    """Oura reports total_sleep_duration in seconds."""
    seconds = _seconds(total_sleep_duration)
    if seconds < 0:
        return None
    return seconds / 60.0
