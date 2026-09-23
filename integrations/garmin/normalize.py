"""Translate Garmin Health summaries into the canonical daily schema.

Stress, Body Battery, and intensity goals are ratings or activity totals,
so they are not copied into the daily measurements. Sleep minutes are the
sum of deep, light, and REM, which leaves awake time out.
"""

from __future__ import annotations

from core.schema import SOURCE_GARMIN
from integrations.frame import canonical_frame


def garmin_to_daily(
    user_id: str,
    dailies: list[dict],
    sleeps: list[dict],
    hrv: list[dict],
    respiration: list[dict],
    skin_temp: list[dict],
):
    by_day: dict[str, dict] = {}
    for document in _one_per_day(dailies):
        day = _day(document)
        if not day:
            continue
        _put(by_day, day, "resting_hr", document.get("restingHeartRateInBeatsPerMinute"))
        _put(by_day, day, "steps", document.get("steps"))
    for document in _longest_sleep(sleeps):
        day = _day(document)
        if not day:
            continue
        _put(by_day, day, "sleep_minutes", _sleep_minutes(document))
        breaths = _mean(document.get("timeOffsetSleepRespiration"))
        if breaths is not None:
            _put(by_day, day, "respiratory_rate", breaths)
    for document in hrv:
        day = _day(document)
        if not day:
            continue
        value = document.get("lastNightAvg")
        if value is None:
            value = (document.get("hrvSummary") or {}).get("lastNightAvg")
        _put(by_day, day, "hrv", value)
    for document in respiration:
        day = _day(document)
        if not day or by_day.get(day, {}).get("respiratory_rate") is not None:
            continue
        _put(by_day, day, "respiratory_rate", document.get("avgWakingRespirationValue"))
    for document in skin_temp:
        day = _day(document)
        if day:
            _put(by_day, day, "skin_temperature_delta", document.get("avgDeviationCelsius"))
    return canonical_frame(user_id, SOURCE_GARMIN, by_day)


def _one_per_day(documents: list[dict]) -> list[dict]:
    chosen: dict[str, dict] = {}
    for document in documents:
        day = _day(document)
        if not day:
            continue
        current = chosen.get(day)
        if current is None or _number(document.get("durationInSeconds")) >= _number(current.get("durationInSeconds")):
            chosen[day] = document
    return list(chosen.values())


def _longest_sleep(documents: list[dict]) -> list[dict]:
    chosen: dict[str, dict] = {}
    for document in documents:
        day = _day(document)
        if not day:
            continue
        current = chosen.get(day)
        if current is None or _sleep_minutes(document) >= _sleep_minutes(current):
            chosen[day] = document
    return list(chosen.values())


def _sleep_minutes(document: dict) -> float:
    stages = (
        _number(document.get("deepSleepDurationInSeconds")),
        _number(document.get("lightSleepDurationInSeconds")),
        _number(document.get("remSleepInSeconds")),
    )
    if any(value >= 0 for value in stages):
        return sum(value for value in stages if value >= 0) / 60.0
    duration = _number(document.get("durationInSeconds"))
    awake = _number(document.get("awakeDurationInSeconds"))
    if duration < 0:
        return 0.0
    if awake >= 0:
        return max(duration - awake, 0.0) / 60.0
    return duration / 60.0


def _mean(samples) -> float | None:
    if not isinstance(samples, dict) or not samples:
        return None
    values = []
    for value in samples.values():
        number = _number(value)
        if number >= 0:
            values.append(number)
    if not values:
        return None
    return sum(values) / len(values)


def _put(by_day: dict[str, dict], day: str, metric: str, value) -> None:
    if value is None:
        return
    by_day.setdefault(day, {})[metric] = value


def _day(document: dict) -> str:
    raw = document.get("calendarDate")
    if raw is None:
        return ""
    return str(raw)[:10]


def _number(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return -1.0
