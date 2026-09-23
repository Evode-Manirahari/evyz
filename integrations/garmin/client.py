"""Fetch Garmin Health summaries, or read a webhook payload from disk.

Garmin delivers dailies, sleep, HRV, respiration, and skin temperature to a
registered application. The pull uses upload time, which is what the Health
API queries. A saved webhook JSON is the same shape.
"""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

from integrations.http import ProviderError, bearer_json

API_BASE = "https://healthapi.garmin.com/wellness-api/rest"
_PATHS = {
    "dailies": "/dailies",
    "sleeps": "/sleeps",
    "hrv": "/hrv",
    "respiration": "/respiration",
    "skinTemp": "/skinTemp",
}


def fetch_history(token: str, start: date, end: date, *, transport=None) -> dict[str, list]:
    get = transport or bearer_json
    query = urlencode(
        {
            "uploadStartTimeInSeconds": _timestamp(start),
            "uploadEndTimeInSeconds": _timestamp(end + timedelta(days=1)),
        }
    )
    found = {name: [] for name in _PATHS}
    for name, path in _PATHS.items():
        url = f"{API_BASE}{path}?{query}"
        try:
            payload = get(url, token)
        except ProviderError as error:
            if error.status == 404:
                continue
            raise
        found[name] = _as_list(payload, name)
    return found


def load_payload(path: Path) -> dict[str, list]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ProviderError(f"{path} must be a JSON object of Garmin summaries.")
    return {name: _as_list(payload.get(name), name) for name in _PATHS}


def _as_list(payload, name: str) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        nested = payload.get(name)
        if isinstance(nested, list):
            return nested
    return []


def _timestamp(day: date) -> int:
    moment = datetime.combine(day, time.min, tzinfo=timezone.utc)
    return int(moment.timestamp())
