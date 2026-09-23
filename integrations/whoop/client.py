"""Fetch WHOOP recovery and sleep with a bearer token.

Scopes used: read:recovery and read:sleep. Profile is not requested.
The end time is exclusive, matching the WHOOP collection routes.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import quote, urlencode

from integrations.http import bearer_json

API_BASE = "https://api.prod.whoop.com/developer"
RECOVERY_PATH = "/v2/recovery"
SLEEP_PATH = "/v2/activity/sleep"


def fetch_history(token: str, start: date, end: date, *, transport=None) -> dict[str, list[dict]]:
    get = transport or bearer_json
    start_at = _iso(start)
    end_at = _iso(end + timedelta(days=1))
    return {
        "recovery": _pages(token, RECOVERY_PATH, start_at, end_at, get),
        "sleep": _pages(token, SLEEP_PATH, start_at, end_at, get),
    }


def _pages(token: str, path: str, start_at: str, end_at: str, transport) -> list[dict]:
    records: list[dict] = []
    next_token = None
    while True:
        url = _url(path, start_at, end_at, next_token)
        payload = transport(url, token)
        records.extend(payload.get("records") or [])
        next_token = payload.get("next_token") or payload.get("nextToken") or None
        if not next_token:
            break
    return records


def _url(path: str, start_at: str, end_at: str, next_token: str | None) -> str:
    if next_token:
        return f"{API_BASE}{path}?nextToken={quote(next_token, safe='')}"
    query = urlencode({"limit": 25, "start": start_at, "end": end_at})
    return f"{API_BASE}{path}?{query}"


def _iso(day: date) -> str:
    moment = datetime.combine(day, time.min, tzinfo=timezone.utc)
    return moment.isoformat()
