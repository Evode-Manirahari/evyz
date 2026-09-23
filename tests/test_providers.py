"""Provider payloads follow the official API shape. They are not a person."""

from __future__ import annotations

from datetime import date

import pandas as pd

from integrations.fitbit.client import fetch_history as fetch_fitbit
from integrations.fitbit.normalize import fitbit_to_daily
from integrations.garmin.client import fetch_history as fetch_garmin
from integrations.garmin.normalize import garmin_to_daily
from integrations.healthkit.normalize import health_export_to_daily
from integrations.http import ProviderError
from integrations.whoop.client import fetch_history as fetch_whoop
from integrations.whoop.normalize import whoop_to_daily


def test_whoop_uses_the_night_and_ignores_the_score_and_absolute_temperature():
    sleep = [
        {
            "id": "nap",
            "nap": True,
            "end": "2024-01-02T18:00:00.000Z",
            "timezone_offset": "-05:00",
            "score_state": "SCORED",
            "score": {
                "stage_summary": {"total_light_sleep_time_milli": 3_600_000},
                "respiratory_rate": 20,
            },
        },
        {
            "id": "night",
            "nap": False,
            "end": "2024-01-02T11:00:00.000Z",
            "timezone_offset": "-05:00",
            "score_state": "SCORED",
            "score": {
                "stage_summary": {
                    "total_light_sleep_time_milli": 14_905_851,
                    "total_slow_wave_sleep_time_milli": 6_630_370,
                    "total_rem_sleep_time_milli": 5_879_573,
                },
                "respiratory_rate": 16.1,
            },
        },
    ]
    recovery = [
        {
            "sleep_id": "nap",
            "score_state": "SCORED",
            "score": {"recovery_score": 90, "resting_heart_rate": 80, "hrv_rmssd_milli": 10},
        },
        {
            "sleep_id": "night",
            "score_state": "SCORED",
            "score": {
                "recovery_score": 44,
                "resting_heart_rate": 64,
                "hrv_rmssd_milli": 31.8,
                "skin_temp_celsius": 33.7,
            },
        },
    ]
    frame = whoop_to_daily("whoop", recovery, sleep)
    row = frame.iloc[0]
    assert row["date"] == pd.Timestamp("2024-01-02")
    assert row["resting_hr"] == 64
    assert row["hrv"] == 31.8
    assert row["sleep_minutes"] == pytest_approx((14_905_851 + 6_630_370 + 5_879_573) / 60_000)
    assert row["respiratory_rate"] == 16.1
    assert pd.isna(row["steps"])
    assert pd.isna(row["skin_temperature_delta"])
    assert row["source"] == "whoop"


def test_whoop_keeps_the_token_out_of_the_url_and_pages():
    seen = []

    def transport(url, token):
        seen.append(url)
        assert "secret-token" not in url
        if "nextToken=" in url:
            return {"records": [], "next_token": None}
        return {"records": [{"id": "1"}], "next_token": "page-2"}

    fetch_whoop("secret-token", date(2024, 1, 1), date(2024, 1, 2), transport=transport)
    first = next(url for url in seen if "nextToken=" not in url)
    assert "end=2024-01-03" in first
    assert any("nextToken=page-2" in url and "start=" not in url for url in seen)


def test_fitbit_prefers_the_main_sleep_and_the_nightly_temperature_change():
    frame = fitbit_to_daily(
        "fitbit",
        heart=[{"dateTime": "2024-01-02", "value": {"restingHeartRate": 62, "heartRateZones": []}}],
        steps=[{"dateTime": "2024-01-02", "value": "8432"}],
        sleep=[
            {"dateOfSleep": "2024-01-02", "minutesAsleep": 30, "isMainSleep": False},
            {"dateOfSleep": "2024-01-02", "minutesAsleep": 420, "isMainSleep": True},
        ],
        hrv=[{"dateTime": "2024-01-02", "value": {"dailyRmssd": 34.9, "deepRmssd": 10}}],
        breathing=[{"dateTime": "2024-01-02", "value": {"breathingRate": 14.8}}],
        skin=[{"dateTime": "2024-01-02", "value": {"nightlyRelative": 0.3}}],
    )
    row = frame.iloc[0]
    assert row["resting_hr"] == 62
    assert row["steps"] == 8432
    assert row["sleep_minutes"] == 420
    assert row["hrv"] == 34.9
    assert row["respiratory_rate"] == 14.8
    assert row["skin_temperature_delta"] == 0.3
    assert row["source"] == "fitbit"


def test_fitbit_splits_a_long_range_into_thirty_day_windows():
    seen = []

    def transport(url, token):
        seen.append(url)
        assert "secret-token" not in url
        return {}

    fetch_fitbit("secret-token", date(2024, 1, 1), date(2024, 2, 9), transport=transport)
    heart = [url for url in seen if "/activities/heart/" in url]
    assert len(heart) == 2
    assert "/2024-01-01/2024-01-30.json" in heart[0]
    assert "/2024-01-31/2024-02-09.json" in heart[1]


def test_garmin_maps_summaries_and_leaves_stress_out():
    frame = garmin_to_daily(
        "garmin",
        dailies=[
            {
                "calendarDate": "2024-01-02",
                "durationInSeconds": 86400,
                "restingHeartRateInBeatsPerMinute": 57,
                "steps": 8432,
                "averageStressLevel": 30,
            }
        ],
        sleeps=[
            {
                "calendarDate": "2024-01-02",
                "deepSleepDurationInSeconds": 5400,
                "lightSleepDurationInSeconds": 14400,
                "remSleepInSeconds": 5400,
                "awakeDurationInSeconds": 1800,
                "timeOffsetSleepRespiration": {"0": 14, "300": 16},
            }
        ],
        hrv=[{"calendarDate": "2024-01-02", "lastNightAvg": 42}],
        respiration=[{"calendarDate": "2024-01-02", "avgWakingRespirationValue": 18}],
        skin_temp=[{"calendarDate": "2024-01-02", "avgDeviationCelsius": 0.2}],
    )
    row = frame.iloc[0]
    assert row["resting_hr"] == 57
    assert row["steps"] == 8432
    assert row["sleep_minutes"] == (5400 + 14400 + 5400) / 60
    assert row["hrv"] == 42
    assert row["respiratory_rate"] == 15
    assert row["skin_temperature_delta"] == 0.2
    assert row["source"] == "garmin"


def test_garmin_pull_ignores_a_missing_collection_and_hides_the_token():
    def transport(url, token):
        assert "secret-token" not in url
        if url.endswith("skinTemp") or "/skinTemp?" in url:
            raise ProviderError("missing", status=404)
        if "/dailies?" in url:
            return [{"calendarDate": "2024-01-02", "steps": 10}]
        return []

    history = fetch_garmin("secret-token", date(2024, 1, 2), date(2024, 1, 2), transport=transport)
    assert history["dailies"][0]["steps"] == 10
    assert history["skinTemp"] == []


def test_apple_health_export_prefers_the_watch_and_asleep_stages(tmp_path):
    export = tmp_path / "export.xml"
    export.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
  <Me HKCharacteristicTypeIdentifierDateOfBirth="1990-01-01"/>
  <Record type="HKQuantityTypeIdentifierHeartRate" sourceName="Apple Watch" unit="count/min" startDate="2024-01-02 08:00:00 -0800" endDate="2024-01-02 08:00:00 -0800" value="120"/>
  <Record type="HKQuantityTypeIdentifierRestingHeartRate" sourceName="Apple Watch" unit="count/min" startDate="2024-01-02 08:00:00 -0800" endDate="2024-01-02 08:00:00 -0800" value="55"/>
  <Record type="HKQuantityTypeIdentifierStepCount" sourceName="iPhone" unit="count" startDate="2024-01-02 10:00:00 -0800" endDate="2024-01-02 10:05:00 -0800" value="10000"/>
  <Record type="HKQuantityTypeIdentifierStepCount" sourceName="Apple Watch" unit="count" startDate="2024-01-02 10:00:00 -0800" endDate="2024-01-02 10:05:00 -0800" value="8000"/>
  <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch" startDate="2024-01-01 23:00:00 -0800" endDate="2024-01-02 06:00:00 -0800" value="HKCategoryValueSleepAnalysisAsleepCore"/>
  <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch" startDate="2024-01-01 22:00:00 -0800" endDate="2024-01-02 07:00:00 -0800" value="HKCategoryValueSleepAnalysisInBed"/>
  <Record type="HKQuantityTypeIdentifierHeartRateVariabilitySDNN" sourceName="Apple Watch" unit="ms" startDate="2024-01-02 06:00:00 -0800" endDate="2024-01-02 06:00:00 -0800" value="42"/>
  <Record type="HKQuantityTypeIdentifierRespiratoryRate" sourceName="Apple Watch" unit="count/min" startDate="2024-01-02 03:00:00 -0800" endDate="2024-01-02 03:00:00 -0800" value="14"/>
  <Record type="HKQuantityTypeIdentifierAppleSleepingWristTemperature" sourceName="Apple Watch" unit="degC" startDate="2024-01-02 06:00:00 -0800" endDate="2024-01-02 06:00:00 -0800" value="0.2"/>
</HealthData>
""",
        encoding="utf-8",
    )
    frame = health_export_to_daily("apple", export)
    row = frame.iloc[0]
    assert row["source"] == "healthkit"
    assert row["resting_hr"] == 55
    assert row["steps"] == 8000
    assert row["sleep_minutes"] == 420
    assert row["hrv"] == 42
    assert row["respiratory_rate"] == 14
    assert row["skin_temperature_delta"] == 0.2
    assert "1990" not in frame.to_csv(index=False)


def pytest_approx(value):
    from pytest import approx

    return approx(value)
