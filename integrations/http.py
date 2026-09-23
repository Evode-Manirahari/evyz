"""Bearer requests for official wearable APIs.

The token is a header. It is never written into the URL or the error text.
"""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ProviderError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def bearer_json(url: str, token: str):
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
        if error.code in (401, 403):
            raise ProviderError(
                f"The provider refused the token ({error.code}). The token was not printed.",
                status=error.code,
            ) from None
        raise ProviderError(
            f"The provider returned {error.code}. {_detail(error)}".strip(),
            status=error.code,
        ) from None
    except URLError as error:
        raise ProviderError(f"Could not reach the provider. {error.reason}") from None
    except json.JSONDecodeError:
        raise ProviderError("The provider returned a response that was not JSON.") from None


def _detail(error: HTTPError) -> str:
    try:
        body = json.loads(error.read().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ""
    detail = body.get("detail") or body.get("errors") if isinstance(body, dict) else None
    if isinstance(detail, str):
        return detail[:300]
    return ""
