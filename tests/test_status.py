"""The first screen reads a real analysis result. The rows are math fixtures."""

from __future__ import annotations

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from apps.api.main import create_app
from apps.api.service import HistoryService
from core.pipeline import PipelineConfig, analyze_person
from core.status import today_status


def _frame(n, **overrides):
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
    return pd.DataFrame(
        {
            "user_id": "user_1",
            "date": dates,
            "resting_hr": columns["resting_hr"],
            "hrv": columns["hrv"],
            "sleep_minutes": columns["sleep"],
            "steps": columns["steps"],
            "respiratory_rate": np.nan,
            "skin_temperature_delta": np.nan,
            "source": "fixture",
        }
    )


def _result(**overrides):
    return analyze_person(_frame(25, **overrides), PipelineConfig())[0]


def test_a_quiet_last_day_says_the_baseline_holds():
    status = today_status(_result())
    assert status["state"] == "steady"
    assert status["headline"] == "Your measurements are close to your recent baseline."
    assert status["signals"]
    assert all(signal["reading"] == "normal" for signal in status["signals"])
    assert "respiratory_rate" not in {signal["metric"] for signal in status["signals"]}


def test_an_ongoing_change_names_the_signals_and_refuses_a_diagnosis():
    status = today_status(
        _result(
            resting_hr=([23, 24], [80.0, 80.0]),
            hrv=([23, 24], [25.0, 25.0]),
            sleep=([23, 24], [300.0, 300.0]),
        )
    )
    assert status["state"] == "change"
    assert status["event"]["duration_days"] == 2
    assert "not a medical diagnosis" in status["event"]["explanation"].lower()
    readings = {item["label"]: item["reading"] for item in status["event"]["changes"]}
    assert readings["Resting heart rate"].endswith("%")
    assert status["timeline"][-1]["in_event"] is True


def test_feedback_is_stored_for_an_event_on_that_history(tmp_path):
    daily = _frame(
        25,
        resting_hr=([23, 24], [80.0, 80.0]),
        hrv=([23, 24], [25.0, 25.0]),
    )
    service = HistoryService(daily, tmp_path / "feedback.jsonl")
    client = TestClient(create_app(service))
    status = client.get("/api/status", params={"user": "user_1"})
    assert status.status_code == 200
    event_id = status.json()["event"]["id"]
    saved = client.post(
        "/api/feedback",
        json={"user_id": "user_1", "event_id": event_id, "label": "stress"},
    )
    assert saved.status_code == 200
    again = client.get("/api/status", params={"user": "user_1"})
    assert again.json()["saved_label"] == "stress"
    rejected = client.post(
        "/api/feedback",
        json={"user_id": "user_1", "event_id": event_id, "label": "pneumonia"},
    )
    assert rejected.status_code == 400


def test_unknown_person_is_not_invented(tmp_path):
    service = HistoryService(_frame(25), tmp_path / "feedback.jsonl")
    client = TestClient(create_app(service))
    missing = client.get("/api/status", params={"user": "nobody"})
    assert missing.status_code == 404
    page = client.get("/")
    assert page.status_code == 200
    assert "What happened around this time?" in page.text
