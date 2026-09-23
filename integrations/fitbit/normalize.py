"""Translate Fitbit summaries into the canonical daily schema.

Heart-rate zones, calories, and the VO2 score are ignored. Skin temperature
uses nightlyRelative, which Fitbit already expresses as a change from the
person's baseline.
"""

from __future__ import annotations

from core.schema import SOURCE_FITBIT
from integrations.frame import canonical_frame


def fitbit_to_daily(
    user_id: str,
    heart: list[dict],
    steps: list[dict],
    sleep: list[dict],
    hrv: list[dict],
    breathing: list[dict],
    skin: list[dict],
):
    by_day: dict[str, dict] = {}
    for document in heart:
        day = _day(document)
        if not day:
            continue
        value = document.get("value") or {}
        _put(by_day, day, "resting_hr", value.get("restingHeartRate"))
    for document in steps:
        day = _day(document)
        if day:
            _put(by_day, day, "steps", document.get("value"))
    for day, document in _main_sleep(sleep).items():
        _put(by_day, day, "sleep_minutes", document.get("minutesAsleep"))
    for document in hrv:
        day = _day(document)
        value = document.get("value") or {}
        if day:
            _put(by_day, day, "hrv", value.get("dailyRmssd"))
    for document in breathing:
        day = _day(document)
        value = document.get("value") or {}
        if day:
            _put(by_day, day, "respiratory_rate", value.get("breathingRate"))
    for document in skin:
        day = _day(document)
        value = document.get("value") or {}
        if day:
            _put(by_day, day, "skin_temperature_delta", value.get("nightlyRelative"))
    return canonical_frame(user_id, SOURCE_FITBIT, by_day)


def _main_sleep(documents: list[dict]) -> dict[str, dict]:
    grouped: dict[str, list[dict]] = {}
    for document in documents:
        day = document.get("dateOfSleep")
        if day:
            grouped.setdefault(str(day)[:10], []).append(document)
    chosen = {}
    for day, nights in grouped.items():
        mains = [night for night in nights if night.get("isMainSleep") is True]
        pool = mains or nights
        chosen[day] = max(pool, key=lambda night: _number(night.get("minutesAsleep")))
    return chosen


def _put(by_day: dict[str, dict], day: str, metric: str, value) -> None:
    by_day.setdefault(day, {})[metric] = value


def _day(document: dict) -> str:
    raw = document.get("dateTime") or document.get("dateOfSleep")
    if raw is None:
        return ""
    return str(raw)[:10]


def _number(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return -1.0
