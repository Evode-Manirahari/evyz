"""Oura document mapping. These payloads match the API shape. They are not a person."""

from __future__ import annotations

from datetime import date

import pandas as pd

from integrations.oura.client import fetch_history
from integrations.oura.normalize import oura_to_daily


def test_long_sleep_beats_a_nap_and_scores_are_not_measurements():
    sleep = [
        {
            "day": "2024-01-02",
            "type": "late_nap",
            "lowest_heart_rate": 70,
            "average_hrv": 80,
            "total_sleep_duration": 1800,
            "average_breath": 16,
        },
        {
            "day": "2024-01-02",
            "type": "long_sleep",
            "lowest_heart_rate": 46,
            "average_hrv": 32,
            "total_sleep_duration": 25200,
            "average_breath": 14.5,
            "readiness": {"temperature_deviation": 0.99},
        },
    ]
    activity = [{"day": "2024-01-02", "steps": 8432}]
    readiness = [
        {
            "day": "2024-01-02",
            "temperature_deviation": 0.12,
            "contributors": {"resting_heart_rate": 81, "hrv_balance": 75},
        }
    ]
    frame = oura_to_daily("oura", sleep, activity, readiness)
    row = frame.iloc[0]
    assert row["source"] == "oura"
    assert row["resting_hr"] == 46
    assert row["hrv"] == 32
    assert row["sleep_minutes"] == 420
    assert row["steps"] == 8432
    assert row["respiratory_rate"] == 14.5
    assert row["skin_temperature_delta"] == 0.12
    assert list(frame.columns) == [
        "user_id",
        "date",
        "resting_hr",
        "hrv",
        "sleep_minutes",
        "steps",
        "respiratory_rate",
        "skin_temperature_delta",
        "source",
    ]


def test_activity_without_sleep_leaves_heart_rate_missing():
    frame = oura_to_daily("oura", [], [{"day": "2024-01-03", "steps": 1000}], [])
    assert pd.isna(frame.iloc[0]["resting_hr"])
    assert frame.iloc[0]["steps"] == 1000


def test_fetch_pads_the_exclusive_end_date_and_keeps_the_token_out_of_the_url():
    seen = []

    def transport(url, token):
        seen.append((url, token))
        assert "secret-token" not in url
        if "next_token=" in url:
            return {
                "data": [{"day": "2024-01-03", "type": "long_sleep", "lowest_heart_rate": 50}],
                "next_token": None,
            }
        return {
            "data": [{"day": "2024-01-02", "type": "long_sleep", "lowest_heart_rate": 48}],
            "next_token": "page-2",
        }

    history = fetch_history("secret-token", date(2024, 1, 1), date(2024, 1, 2), transport=transport)
    first_sleep = next(url for url, _token in seen if "/sleep?" in url and "next_token=" not in url)
    assert "start_date=2024-01-01" in first_sleep
    assert "end_date=2024-01-03" in first_sleep
    assert any("next_token=page-2" in url and "start_date" not in url for url, _token in seen)
    assert [document["day"] for document in history["sleep"]] == ["2024-01-02"]
