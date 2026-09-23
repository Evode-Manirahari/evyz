"""Validate the label a person attaches to an event.

These are the patient labels. A clinician label is a separate, later set.
"""

from __future__ import annotations

from datetime import datetime, timezone

from core.schema import FEEDBACK_LABELS


def feedback_record(*, user_id: str, event_id: str, label: str, notes: str | None = None) -> dict:
    if label not in FEEDBACK_LABELS:
        allowed = ", ".join(FEEDBACK_LABELS)
        raise ValueError(f"Unknown feedback label {label!r}. Expected one of: {allowed}")
    return {
        "user_id": user_id,
        "event_id": event_id,
        "label": label,
        "notes": notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
