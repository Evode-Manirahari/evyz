"""Fetch Fitbit daily summaries with a bearer token.

Requests use the current-user id "-" and stay inside 30-day windows, which
is the longest range the HRV route accepts. Profile is not requested.
"""

from __future__ import annotations

from datetime import date, timedelta

from integrations.http import bearer_json

API_BASE = "https://api.fitbit.com"
_ROUTES = {
    "heart": "/1/user/-/activities/heart/date/{start}/{end}.json",
    "steps": "/1/user/-/activities/steps/date/{start}/{end}.json",
    "sleep": "/1.2/user/-/sleep/date/{start}/{end}.json",
    "hrv": "/1/user/-/hrv/date/{start}/{end}.json",
    "breathing": "/1/user/-/br/date/{start}/{end}.json",
    "skin": "/1/user/-/temp/skin/date/{start}/{end}.json",
}
_LIST_KEYS = {
    "heart": "activities-heart",
    "steps": "activities-steps",
    "sleep": "sleep",
    "hrv": "hrv",
    "breathing": "br",
    "skin": "tempSkin",
}


def fetch_history(token: str, start: date, end: date, *, transport=None) -> dict[str, list[dict]]:
    get = transport or bearer_json
    merged = {name: [] for name in _ROUTES}
    for chunk_start, chunk_end in _windows(start, end, 30):
        for name, route in _ROUTES.items():
            url = API_BASE + route.format(start=chunk_start.isoformat(), end=chunk_end.isoformat())
            payload = get(url, token)
            merged[name].extend(payload.get(_LIST_KEYS[name]) or [])
    return merged


def _windows(start: date, end: date, size: int):
    cursor = start
    while cursor <= end:
        stop = min(end, cursor + timedelta(days=size - 1))
        yield cursor, stop
        cursor = stop + timedelta(days=1)
