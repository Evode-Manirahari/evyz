"""Fetch Oura daily collections with a bearer token.

The sleep route treats end_date as exclusive, so every request asks for one
extra day and then drops anything outside the inclusive window. The token is
sent as a header and is never placed in the URL.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

API_BASE = "https://api.ouraring.com"
SLEEP_PATH = "/v2/usercollection/sleep"
ACTIVITY_PATH = "/v2/usercollection/daily_activity"
READINESS_PATH = "/v2/usercollection/daily_readiness"


class OuraError(RuntimeError):
    pass


def fetch_history(token: str, start: date, end: date, *, transport=None) -> dict[str, list[dict]]:
    if end < start:
        raise OuraError("The end date is before the start date.")
    get = transport or _urllib_get
    return {
        "sleep": _collection(token, SLEEP_PATH, start, end, get),
        "activity": _collection(token, ACTIVITY_PATH, start, end, get),
        "readiness": _collection(token, READINESS_PATH, start, end, get),
    }


def _collection(token: str, path: str, start: date, end: date, transport) -> list[dict]:
    documents: list[dict] = []
    next_token = None
    while True:
        url = _collection_url(path, start, end, next_token)
        payload = transport(url, token)
        documents.extend(payload.get("data") or [])
        next_token = payload.get("next_token") or None
        if not next_token:
            break
    return [document for document in documents if _inside(document, start, end)]


def _collection_url(path: str, start: date, end: date, next_token: str | None) -> str:
    if next_token:
        return f"{API_BASE}{path}?next_token={quote(next_token, safe='')}"
    # One extra day because /sleep treats end_date as exclusive.
    query = urlencode(
        {
            "start_date": start.isoformat(),
            "end_date": (end + timedelta(days=1)).isoformat(),
        }
    )
    return f"{API_BASE}{path}?{query}"


def _inside(document: dict, start: date, end: date) -> bool:
    raw = document.get("day")
    if not raw:
        return False
    try:
        day = date.fromisoformat(str(raw)[:10])
    except ValueError:
        return False
    return start <= day <= end


def _urllib_get(url: str, token: str) -> dict:
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = _error_detail(error)
        if error.code in (401, 403):
            raise OuraError(
                f"Oura refused the token ({error.code}). "
                "Create a personal access token with the daily scope, "
                "and set OURA_ACCESS_TOKEN. The token was not printed."
            ) from None
        raise OuraError(f"Oura returned {error.code}. {detail}".strip()) from None
    except URLError as error:
        raise OuraError(f"Could not reach Oura. {error.reason}") from None
    except json.JSONDecodeError:
        raise OuraError("Oura returned a response that was not JSON.") from None


def _error_detail(error: HTTPError) -> str:
    try:
        body = json.loads(error.read().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ""
    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, str):
        return detail[:300]
    return ""
