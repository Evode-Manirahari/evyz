"""Rule tests for the daily baseline and event logic.

The rows here are fixtures for the math. They are not a stand-in for a person,
and they are not the phase-0 dataset.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.feedback.labels import feedback_record
from core.normalization.wearableqa import days_to_frame
from core.pipeline import PipelineConfig, analyze_person
from core.quality.checks import apply_quality


def _frame(dates, resting_hr, hrv, sleep, steps, user_id="user_1"):
    return pd.DataFrame(
        {
            "user_id": user_id,
            "date": dates,
            "resting_hr": resting_hr,
            "hrv": hrv,
            "sleep_minutes": sleep,
            "steps": steps,
            "respiratory_rate": np.nan,
            "skin_temperature_delta": np.nan,
            "source": "fixture",
        }
    )


def _steady(n, **overrides):
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    columns = {
        "resting_hr": [60.0] * n,
        "hrv": [50.0] * n,
        "sleep": [420.0] * n,
        "steps": [8000.0] * n,
    }
    for key, (index, value) in overrides.items():
        for day, replacement in zip(index, value):
            columns[key][day] = replacement
    return _frame(dates, columns["resting_hr"], columns["hrv"], columns["sleep"], columns["steps"])


def test_baseline_excludes_the_current_day():
    frame = _steady(20, resting_hr=([19], [100.0]))
    result = analyze_person(frame, PipelineConfig())[0]
    last = result.features.iloc[-1]
    assert last["resting_hr_baseline"] == 60.0
    assert last["resting_hr"] == 100.0


def test_two_signals_for_two_days_become_one_event():
    frame = _steady(
        25,
        resting_hr=([20, 21], [80.0, 80.0]),
        hrv=([20, 21], [25.0, 25.0]),
        sleep=([20, 21], [300.0, 300.0]),
    )
    result = analyze_person(frame, PipelineConfig())[0]
    assert result.usable
    assert len(result.events) == 1
    event = result.events[0]
    assert event.rule == "multi_signal"
    assert event.duration_days == 2
    assert event.signals == ["resting_hr", "hrv", "sleep_minutes"]
    assert "not a medical diagnosis" in event.explanation.lower()
    assert "steps" not in event.signals


def test_a_strong_tail_does_not_repeat_days_already_in_an_event():
    frame = _steady(
        28,
        resting_hr=([20, 21], [90.0, 90.0]),
        steps=([20, 21, 22], [20000.0, 20000.0, 20000.0]),
    )
    events = analyze_person(frame, PipelineConfig())[0].events
    assert len(events) == 1
    assert events[0].rule == "multi_signal"
    assert events[0].start_date == pd.Timestamp("2024-01-21")
    assert events[0].end_date == pd.Timestamp("2024-01-22")


def test_a_long_strong_tail_starts_after_the_multi_signal_event():
    frame = _steady(
        28,
        resting_hr=([20, 21], [90.0, 90.0]),
        steps=([20, 21, 22, 23], [20000.0, 20000.0, 20000.0, 20000.0]),
    )
    events = analyze_person(frame, PipelineConfig())[0].events
    assert [(event.rule, event.start_date.date().isoformat(), event.end_date.date().isoformat()) for event in events] == [
        ("multi_signal", "2024-01-21", "2024-01-22"),
        ("strong_single", "2024-01-23", "2024-01-24"),
    ]
    assert events[1].signals == ["steps"]


def test_one_strong_signal_persisting_is_an_event():
    frame = _steady(25, resting_hr=([20, 21], [90.0, 90.0]))
    result = analyze_person(frame, PipelineConfig())[0]
    assert len(result.events) == 1
    event = result.events[0]
    assert event.rule == "strong_single"
    assert event.signals == ["resting_hr"]


def test_a_single_unusual_day_is_not_an_event():
    frame = _steady(
        24,
        resting_hr=([20], [90.0]),
        hrv=([20], [25.0]),
        sleep=([20], [300.0]),
    )
    result = analyze_person(frame, PipelineConfig())[0]
    assert result.events == []


def test_short_history_is_insufficient():
    frame = _steady(10)
    result = analyze_person(frame, PipelineConfig())[0]
    assert not result.usable
    assert "Insufficient data" in result.reasons[0]


def test_a_long_gap_does_not_reuse_the_old_baseline():
    early = pd.date_range("2024-01-01", periods=20, freq="D")
    late = pd.date_range("2024-03-01", periods=2, freq="D")
    frame = _frame(
        list(early) + list(late),
        [60.0] * 20 + [90.0, 90.0],
        [50.0] * 22,
        [420.0] * 22,
        [8000.0] * 22,
    )
    results = analyze_person(frame, PipelineConfig())
    assert len(results) == 2
    assert results[0].usable
    assert results[0].events == []
    assert not results[1].usable


def test_implausible_resting_hr_becomes_missing():
    frame = _steady(2)
    frame.loc[0, "resting_hr"] = 10
    cleaned, removed = apply_quality(frame)
    assert removed["resting_hr"] == 1
    assert pd.isna(cleaned.loc[0, "resting_hr"])
    assert cleaned.loc[1, "resting_hr"] == 60


def test_sleep_hours_become_minutes():
    frame = days_to_frame(
        "user_9",
        [
            {"date": "2024-01-01", "rhr": 61, "hrv": 42, "sleep_duration": 7.0, "steps": 8000},
            {"date": "2024-01-02", "rhr": 60, "hrv": 45, "sleep_minutes": 400, "steps": 7000},
        ],
    )
    assert frame.loc[0, "sleep_minutes"] == 420
    assert frame.loc[1, "sleep_minutes"] == 400
    assert frame.loc[0, "resting_hr"] == 61
    assert "blood" not in frame.columns


def test_feedback_label_must_be_known():
    record = feedback_record(user_id="user_1", event_id="e1", label="poor_sleep")
    assert record["label"] == "poor_sleep"
    with pytest.raises(ValueError):
        feedback_record(user_id="user_1", event_id="e1", label="pneumonia")


def test_explanation_does_not_diagnose():
    frame = _steady(
        25,
        resting_hr=([20, 21], [80.0, 80.0]),
        hrv=([20, 21], [25.0, 25.0]),
    )
    text = analyze_person(frame, PipelineConfig())[0].events[0].explanation.lower()
    for phrase in ("pneumonia", "heart failure", "heart attack", "covid", "evyz score"):
        assert phrase not in text
