"""Canonical daily wearable schema.

Provider-specific names stop here. Later engines read these columns only.
Respiratory rate and skin-temperature delta stay in the schema so a later
source can fill them. This dataset does not have to provide every column.
"""

from __future__ import annotations

SOURCE_WEARABLEQA = "wearableqa"
SOURCE_OURA = "oura"
SOURCE_WHOOP = "whoop"
SOURCE_FITBIT = "fitbit"
SOURCE_GARMIN = "garmin"
SOURCE_HEALTHKIT = "healthkit"

DAILY_METRICS = (
    "resting_hr",
    "hrv",
    "sleep_minutes",
    "steps",
    "respiratory_rate",
    "skin_temperature_delta",
)

DAILY_COLUMNS = ("user_id", "date", *DAILY_METRICS, "source")

UNITS = {
    "resting_hr": "bpm",
    "hrv": "source_units",
    "sleep_minutes": "minutes",
    "steps": "steps",
    "respiratory_rate": "breaths_per_min",
    "skin_temperature_delta": "celsius",
}

# WearableQA does not document HRV as RMSSD. Keep the source name.
METRIC_LABELS = {
    "resting_hr": "Resting heart rate",
    "hrv": "Heart-rate variability",
    "sleep_minutes": "Sleep",
    "steps": "Steps",
    "respiratory_rate": "Respiratory rate",
    "skin_temperature_delta": "Skin temperature change",
}

# Inclusive ranges. Values outside these become missing, not events.
PLAUSIBLE = {
    "resting_hr": (30.0, 220.0),
    "hrv": (1.0, 300.0),
    "sleep_minutes": (1.0, 16 * 60),
    "steps": (0.0, 150_000.0),
    "respiratory_rate": (4.0, 60.0),
    "skin_temperature_delta": (-5.0, 5.0),
}

# Keeps a perfectly flat baseline from producing an infinite z-score.
MAD_FLOOR = {
    "resting_hr": 1.0,
    "hrv": 2.0,
    "sleep_minutes": 15.0,
    "steps": 500.0,
    "respiratory_rate": 0.4,
    "skin_temperature_delta": 0.05,
}

PERCENT_FLOOR = {
    "resting_hr": 20.0,
    "hrv": 5.0,
    "sleep_minutes": 60.0,
    "steps": 1000.0,
    "respiratory_rate": 4.0,
    "skin_temperature_delta": 0.05,
}

# What the person says happened. Clinician labels are a later set.
FEEDBACK_LABELS = (
    "sick",
    "poor_sleep",
    "stress",
    "hard_workout",
    "travel",
    "medication_change",
    "treatment_side_effect",
    "nothing_noticeable",
    "other",
)
