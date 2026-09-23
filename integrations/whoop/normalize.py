"""Translate WHOOP recovery and sleep into the canonical daily schema.

The recovery score is a 0–100 rating and is ignored. Skin temperature from
WHOOP is an absolute Celsius reading, not a change from the person's baseline,
so it is left empty. WHOOP does not provide steps.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from core.schema import SOURCE_WHOOP
from integrations.frame import canonical_frame

_SLEEP_STAGES = (
    "total_light_sleep_time_milli",
    "total_slow_wave_sleep_time_milli",
    "total_rem_sleep_time_milli",
)


def whoop_to_daily(user_id: str, recovery: list[dict], sleep: list[dict]):
    nights = _nights(sleep)
    recovery_by_sleep = {}
    for document in recovery:
        if document.get("score_state") not in (None, "SCORED"):
            continue
        sleep_id = document.get("sleep_id")
        if sleep_id:
            recovery_by_sleep[sleep_id] = document.get("score") or {}
    by_day: dict[str, dict] = {}
    for day, night in nights.items():
        score = recovery_by_sleep.get(night.get("id")) or {}
        by_day[day] = {
            "resting_hr": score.get("resting_heart_rate"),
            "hrv": score.get("hrv_rmssd_milli"),
            "sleep_minutes": _sleep_minutes(night),
            "respiratory_rate": (night.get("score") or {}).get("respiratory_rate"),
        }
    return canonical_frame(user_id, SOURCE_WHOOP, by_day)


def _nights(sleep: list[dict]) -> dict[str, dict]:
    chosen: dict[str, dict] = {}
    for document in sleep:
        if document.get("nap") is True:
            continue
        if document.get("score_state") not in (None, "SCORED"):
            continue
        day = _local_day(document.get("end"), document.get("timezone_offset"))
        if not day:
            continue
        current = chosen.get(day)
        if current is None or _sleep_minutes(document) > _sleep_minutes(current):
            chosen[day] = document
    return chosen


def _sleep_minutes(document: dict) -> float:
    stages = (document.get("score") or {}).get("stage_summary") or {}
    millis = 0.0
    for key in _SLEEP_STAGES:
        value = stages.get(key)
        if value is None:
            continue
        millis += float(value)
    if millis <= 0:
        return 0.0
    return millis / 60_000.0


def _local_day(timestamp: str | None, offset: str | None) -> str:
    if not timestamp:
        return ""
    moment = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    if offset and moment.utcoffset() == timedelta(0):
        sign = -1 if str(offset).startswith("-") else 1
        hours, minutes = str(offset).lstrip("+-").split(":")
        moment = moment + timedelta(hours=sign * int(hours), minutes=sign * int(minutes))
    return moment.date().isoformat()
