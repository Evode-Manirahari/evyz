"""Turn one analyzed timeline into the first screen.

The last day of the timeline is "today." A past event stays available to
read and label. One unusual day still does not become an event.
"""

from __future__ import annotations

import math

import pandas as pd

from core.events.events import ChangeEvent
from core.pipeline import SegmentResult
from core.schema import DAILY_METRICS, FEEDBACK_LABELS, METRIC_LABELS

LABEL_TITLES = {
    "sick": "Sick",
    "poor_sleep": "Poor sleep",
    "stress": "Stress",
    "hard_workout": "Hard workout",
    "travel": "Travel",
    "medication_change": "Medication change",
    "treatment_side_effect": "Treatment side effect",
    "nothing_noticeable": "Nothing noticeable",
    "other": "Other",
}


def latest_segment(results: list[SegmentResult]) -> SegmentResult | None:
    if not results:
        return None
    usable = [item for item in results if item.usable]
    pool = usable or results
    return max(pool, key=lambda item: pd.Timestamp(item.end_date))


def event_id(event: ChangeEvent) -> str:
    signals = "-".join(event.signals)
    day = pd.Timestamp(event.start_date).date().isoformat()
    return f"{event.user_id}:{day}:{event.rule}:{signals}"


def today_status(result: SegmentResult, *, selected_event_id: str | None = None, saved_label: str | None = None) -> dict:
    labels = [{"id": label, "title": LABEL_TITLES[label]} for label in FEEDBACK_LABELS]
    if not result.usable or result.features is None or result.features.empty:
        return {
            "user_id": result.user_id,
            "source": None,
            "date": pd.Timestamp(result.end_date).date().isoformat(),
            "state": "insufficient",
            "headline": "Insufficient data.",
            "detail": result.reasons[0] if result.reasons else "Not enough history for a personal baseline.",
            "signals": [],
            "event": None,
            "events": [],
            "timeline": [],
            "saved_label": None,
            "labels": labels,
        }
    features = result.features
    row = features.iloc[-1]
    day = pd.Timestamp(row["date"])
    events = [_event_summary(event) for event in result.events]
    active = next((event for event in result.events if _covers(event, day)), None)
    selected = _select_event(result.events, selected_event_id, active)
    state = "change" if active is not None else "steady"
    if state == "change":
        headline = "Your physiology is different from your recent normal pattern."
        detail = f"Duration {active.duration_days} days."
    else:
        headline = "Your measurements are close to your recent baseline."
        detail = "Compared with this person's previous days, not a population range."
    return {
        "user_id": result.user_id,
        "source": None if pd.isna(row["source"]) else str(row["source"]),
        "date": day.date().isoformat(),
        "state": state,
        "headline": headline,
        "detail": detail,
        "signals": _signals(row),
        "event": None if selected is None else _event_detail(selected),
        "events": events,
        "timeline": _timeline(features, result.events),
        "saved_label": saved_label,
        "labels": labels,
    }


def _select_event(events: list[ChangeEvent], selected_event_id: str | None, active: ChangeEvent | None) -> ChangeEvent | None:
    if selected_event_id:
        for event in events:
            if event_id(event) == selected_event_id:
                return event
    if active is not None:
        return active
    if not events:
        return None
    return events[-1]


def _covers(event: ChangeEvent, day: pd.Timestamp) -> bool:
    return pd.Timestamp(event.start_date) <= day <= pd.Timestamp(event.end_date)


def _signals(row: pd.Series) -> list[dict]:
    signals = []
    for metric in DAILY_METRICS:
        level = str(row[f"{metric}_level"])
        if level == "missing":
            continue
        signals.append(
            {
                "metric": metric,
                "label": METRIC_LABELS[metric],
                "level": level,
                "reading": _reading(
                    level,
                    row[f"{metric}_pct"],
                    row[metric],
                    row[f"{metric}_baseline"],
                ),
            }
        )
    return signals


def _reading(level: str, percent, value, baseline) -> str:
    if level in {"unusual", "strong"} and _finite(percent):
        return f"{float(percent):+.0f}%"
    if level in {"unusual", "strong"}:
        if _finite(value) and _finite(baseline) and float(value) < float(baseline):
            return "below your range"
        return "above your range"
    if level == "normal" and _finite(percent) and float(percent) <= -5:
        return "slightly lower"
    if level == "normal" and _finite(percent) and float(percent) >= 5:
        return "slightly higher"
    return "normal"


def _event_summary(event: ChangeEvent) -> dict:
    return {
        "id": event_id(event),
        "start_date": pd.Timestamp(event.start_date).date().isoformat(),
        "end_date": pd.Timestamp(event.end_date).date().isoformat(),
        "duration_days": event.duration_days,
        "status": event.status,
        "signals": [METRIC_LABELS[metric] for metric in event.signals],
    }


def _event_detail(event: ChangeEvent) -> dict:
    summary = _event_summary(event)
    summary["explanation"] = event.explanation
    summary["changes"] = [
        {
            "label": METRIC_LABELS[metric],
            "reading": _event_reading(event.metrics[metric]),
        }
        for metric in event.signals
    ]
    return summary


def _event_reading(summary: dict) -> str:
    percent = summary.get("percent")
    if percent is None or not _finite(percent):
        return summary["direction"]
    return f"{float(percent):+.0f}%"


def _timeline(features: pd.DataFrame, events: list[ChangeEvent]) -> list[dict]:
    tail = features.tail(14)
    rows = []
    for _, row in tail.iterrows():
        day = pd.Timestamp(row["date"])
        rows.append(
            {
                "date": day.date().isoformat(),
                "in_event": any(_covers(event, day) for event in events),
                "signals": _signals(row),
            }
        )
    return rows


def _finite(value) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False
