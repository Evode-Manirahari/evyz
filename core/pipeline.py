"""Run one person's daily history through quality, baseline, and events."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from core.baseline.baseline import add_baselines, split_segments
from core.detection.detect import add_deviation_labels
from core.events.events import ChangeEvent, build_events
from core.features.features import add_personalized_features
from core.insights.explain import explain_event
from core.quality.checks import apply_quality
from core.schema import DAILY_METRICS


@dataclass(frozen=True)
class PipelineConfig:
    baseline_window: int = 28
    min_baseline_days: int = 14
    unusual_z: float = 2.0
    strong_z: float = 3.0
    min_persist_days: int = 2
    max_gap_days: int = 3


@dataclass
class SegmentResult:
    user_id: str
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    n_observed_resting_hr: int
    usable: bool
    reasons: list[str] = field(default_factory=list)
    features: pd.DataFrame | None = None
    events: list[ChangeEvent] = field(default_factory=list)


def analyze_person(daily: pd.DataFrame, config: PipelineConfig | None = None) -> list[SegmentResult]:
    config = config or PipelineConfig()
    cleaned, _removed = apply_quality(daily)
    if cleaned.empty:
        return []
    results = []
    for segment in split_segments(cleaned, max_gap_days=config.max_gap_days):
        results.append(_analyze_segment(segment, config))
    return results


def _analyze_segment(segment: pd.DataFrame, config: PipelineConfig) -> SegmentResult:
    user_id = str(segment["user_id"].dropna().iloc[0])
    start_date = pd.Timestamp(segment["date"].iloc[0])
    end_date = pd.Timestamp(segment["date"].iloc[-1])
    observed = int(pd.to_numeric(segment["resting_hr"], errors="coerce").notna().sum())
    base = SegmentResult(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        n_observed_resting_hr=observed,
        usable=False,
    )
    if observed < config.min_baseline_days:
        base.reasons = ["Insufficient data. Not enough resting-heart-rate history for a personal baseline."]
        return base
    available = [
        metric
        for metric in DAILY_METRICS
        if pd.to_numeric(segment[metric], errors="coerce").notna().sum() >= config.min_baseline_days
    ]
    if len(available) < 1:
        base.reasons = ["Insufficient data. No signal has enough history."]
        return base
    featured = add_baselines(segment, window=config.baseline_window, min_periods=config.min_baseline_days)
    featured = add_personalized_features(featured)
    featured = add_deviation_labels(
        featured,
        unusual_z=config.unusual_z,
        strong_z=config.strong_z,
        min_baseline_days=config.min_baseline_days,
    )
    if featured["resting_hr_baseline"].notna().sum() == 0:
        base.reasons = ["Insufficient data. The resting-heart-rate baseline never became stable."]
        return base
    events = build_events(featured, min_days=config.min_persist_days, unusual_z=config.unusual_z)
    for event in events:
        event.explanation = explain_event(event)
    base.usable = True
    base.features = featured
    base.events = events
    return base
