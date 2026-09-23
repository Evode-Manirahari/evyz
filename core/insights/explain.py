"""Describe an event from the days and signals that produced it."""

from __future__ import annotations

from core.events.events import ChangeEvent
from core.schema import METRIC_LABELS

_FORMATS = {
    "resting_hr": "{:.1f} bpm",
    "hrv": "{:.1f}",
    "sleep_minutes": "{:.0f} min",
    "steps": "{:.0f} steps",
    "respiratory_rate": "{:.1f} breaths/min",
    "skin_temperature_delta": "{:+.2f} °C",
}


def explain_event(event: ChangeEvent) -> str:
    day_word = "day" if event.duration_days == 1 else "days"
    lines = [
        "EVYZ detected a change because the measurements moved away from",
        "this person's own recent range.",
        "",
        f"It began on {event.start_date.date().isoformat()} and lasted {event.duration_days} {day_word}.",
        f"Status: {event.status}.",
        "",
        "What changed:",
    ]
    for metric in event.signals:
        lines.append(_metric_line(metric, event.metrics[metric]))
    lines.append("")
    lines.append(_prose(event))
    if event.recovery_days is not None:
        later = "day" if event.recovery_days == 1 else "days"
        lines.append(
            f"The included signals were back inside the recent range {event.recovery_days} {later} later."
        )
    lines.extend(
        [
            "",
            "The baseline is the previous 28 days for this person, excluding the current day.",
            "This is a description of the measurements. It is not a medical diagnosis.",
        ]
    )
    return "\n".join(lines)


def _metric_line(metric: str, summary: dict) -> str:
    label = METRIC_LABELS[metric]
    baseline = _FORMATS[metric].format(summary["baseline"])
    during = _FORMATS[metric].format(summary["during"])
    if summary["percent"] is None:
        change = summary["direction"] + " the recent range"
    else:
        change = f"{summary['percent']:+.1f}% ({summary['direction']} the recent range)"
    low = _FORMATS[metric].format(summary["p10"])
    high = _FORMATS[metric].format(summary["p90"])
    return f"- {label}: recent range {low} to {high}, baseline {baseline}, during this period {during}, {change}."


def _prose(event: ChangeEvent) -> str:
    pieces = []
    for metric in event.signals:
        summary = event.metrics[metric]
        label = METRIC_LABELS[metric]
        if summary["direction"] == "above":
            pieces.append(f"{label} stayed above the recent range")
        elif summary["direction"] == "below":
            pieces.append(f"{label} stayed below the recent range")
        else:
            pieces.append(f"{label} moved away from the recent range")
    if len(pieces) == 1:
        body = pieces[0]
    else:
        body = ", ".join(pieces[:-1]) + f", and {pieces[-1]}"
    return f"{body} for {event.duration_days} days."
