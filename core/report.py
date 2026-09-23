"""Text reports for one timeline and for the cohort summary."""

from __future__ import annotations

import pandas as pd

from core.pipeline import SegmentResult
from core.schema import DAILY_METRICS, METRIC_LABELS, UNITS

_FORMATS = {
    "resting_hr": "{:.1f}",
    "hrv": "{:.1f}",
    "sleep_minutes": "{:.0f}",
    "steps": "{:.0f}",
    "respiratory_rate": "{:.1f}",
    "skin_temperature_delta": "{:+.2f}",
}


def format_segment(result: SegmentResult, *, events_file: str = "data/processed/events.csv") -> str:
    lines = [
        f"PERSON {result.user_id}",
        f"TIMELINE {result.start_date.date().isoformat()} to {result.end_date.date().isoformat()}",
        f"Resting-heart-rate days: {result.n_observed_resting_hr}",
        "",
    ]
    if not result.usable or result.features is None:
        lines.append("INSUFFICIENT DATA")
        lines.extend(f"- {reason}" for reason in result.reasons)
        return "\n".join(lines)
    row = _reference_row(result)
    lines.extend(
        [
            "28-DAY BASELINE",
            "────────────────────────",
            "Compared with this person's previous days, not a population range.",
            "",
        ]
    )
    for metric in DAILY_METRICS:
        baseline = row[f"{metric}_baseline"]
        if pd.isna(baseline):
            continue
        label = METRIC_LABELS[metric]
        unit = UNITS[metric]
        center = _FORMATS[metric].format(baseline)
        low = _FORMATS[metric].format(row[f"{metric}_p10"])
        high = _FORMATS[metric].format(row[f"{metric}_p90"])
        lines.append(f"{label}: {center} {unit}  (central range {low}–{high})")
    lines.append("")
    if not result.events:
        lines.append("No multi-signal or persistent strong change met the rule on this timeline.")
        return "\n".join(lines)
    multi = [event for event in result.events if event.rule == "multi_signal"]
    shown = multi[:2] or result.events[:1]
    lines.append(f"EVYZ EVENTS ON THIS TIMELINE: {len(result.events)}")
    for event in shown:
        lines.append("")
        lines.append(event.explanation)
    hidden = len(result.events) - len(shown)
    if hidden:
        lines.append("")
        lines.append(f"{hidden} other events from this timeline are in {events_file}.")
    return "\n".join(lines)


def format_summary(
    results: list[SegmentResult],
    *,
    heading: str = "PHASE 0 SUMMARY",
    note: str = "WearableQA questions are not used as event labels.",
) -> str:
    users = {item.user_id for item in results}
    usable = [item for item in results if item.usable]
    with_events = [item for item in usable if item.events]
    event_counts = []
    for user_id in {item.user_id for item in usable}:
        event_counts.append(sum(len(item.events) for item in usable if item.user_id == user_id))
    median = None if not event_counts else float(pd.Series(event_counts).median())
    rule_counts = {"multi_signal": 0, "strong_single": 0}
    for item in usable:
        for event in item.events:
            rule_counts[event.rule] = rule_counts.get(event.rule, 0) + 1
    lines = [
        heading,
        "────────────────────────",
        f"People: {len(users)}",
        f"Timelines with a personal baseline: {len(usable)}",
        f"Timelines with at least one event: {len(with_events)}",
        f"Events: {sum(len(item.events) for item in usable)}",
        f"  multi-signal: {rule_counts.get('multi_signal', 0)}",
        f"  one strong signal, persisted: {rule_counts.get('strong_single', 0)}",
        f"Median events per person with a baseline: {median}",
        "",
        "These counts are not a medical evaluation.",
        note,
    ]
    return "\n".join(lines)


def choose_segment(results: list[SegmentResult], user_id: str | None = None) -> SegmentResult | None:
    pool = results
    if user_id:
        pool = [item for item in results if item.user_id == user_id]
    usable = [item for item in pool if item.usable]
    if not usable:
        return pool[0] if pool else None
    return max(
        usable,
        key=lambda item: (
            sum(event.rule == "multi_signal" for event in item.events),
            item.n_observed_resting_hr,
        ),
    )


def _reference_row(result: SegmentResult) -> pd.Series:
    features = result.features
    if result.events:
        day = result.events[0].start_date
        match = features.loc[pd.to_datetime(features["date"]) == day]
        if not match.empty:
            return match.iloc[0]
    ready = features.loc[features["resting_hr_baseline"].notna()]
    return ready.iloc[-1]
