"""Turn an Apple Health export.xml into the canonical daily schema.

The export is the file produced by the Health app's Export All Health Data.
Identity fields on the Me element are ignored. Wrist temperature is already
a change from the person's baseline. Heart-rate variability here is SDNN,
stored in the hrv column without renaming it.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median
from xml.etree import ElementTree

from core.schema import SOURCE_HEALTHKIT
from integrations.frame import canonical_frame

_RESTING = "HKQuantityTypeIdentifierRestingHeartRate"
_HRV = "HKQuantityTypeIdentifierHeartRateVariabilitySDNN"
_STEPS = "HKQuantityTypeIdentifierStepCount"
_BREATH = "HKQuantityTypeIdentifierRespiratoryRate"
_TEMP = "HKQuantityTypeIdentifierAppleSleepingWristTemperature"
_SLEEP = "HKCategoryTypeIdentifierSleepAnalysis"
_ASLEEP = {
    "HKCategoryValueSleepAnalysisAsleep",
    "HKCategoryValueSleepAnalysisAsleepUnspecified",
    "HKCategoryValueSleepAnalysisAsleepCore",
    "HKCategoryValueSleepAnalysisAsleepDeep",
    "HKCategoryValueSleepAnalysisAsleepREM",
}


def health_export_to_daily(user_id: str, path: Path):
    return records_to_daily(user_id, _iter_records(path))


def records_to_daily(user_id: str, records: list[dict]):
    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        kind = record.get("type")
        if kind:
            grouped[kind].append(record)
    by_day: dict[str, dict] = {}
    _quantity(by_day, grouped[_RESTING], "resting_hr", total=False)
    _quantity(by_day, grouped[_HRV], "hrv", total=False)
    _quantity(by_day, grouped[_STEPS], "steps", total=True)
    _quantity(by_day, grouped[_BREATH], "respiratory_rate", total=False)
    _quantity(by_day, grouped[_TEMP], "skin_temperature_delta", total=False)
    _sleep(by_day, grouped[_SLEEP])
    return canonical_frame(user_id, SOURCE_HEALTHKIT, by_day)


def _iter_records(path: Path):
    records = []
    for _, element in ElementTree.iterparse(path, events=("end",)):
        if element.tag != "Record":
            continue
        records.append(dict(element.attrib))
        element.clear()
    return records


def _quantity(by_day: dict[str, dict], records: list[dict], metric: str, *, total: bool) -> None:
    samples: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        moment = _parse(record.get("endDate") or record.get("startDate"))
        value = _number(record.get("value"))
        if moment is None or value is None:
            continue
        samples[moment.date().isoformat()].append(
            {"source": str(record.get("sourceName") or ""), "value": value}
        )
    for day, group in samples.items():
        chosen = _prefer_watch(group, total=total)
        values = [item["value"] for item in chosen]
        by_day.setdefault(day, {})[metric] = sum(values) if total else median(values)


def _sleep(by_day: dict[str, dict], records: list[dict]) -> None:
    samples: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        if record.get("value") not in _ASLEEP:
            continue
        start = _parse(record.get("startDate"))
        end = _parse(record.get("endDate"))
        if start is None or end is None or end <= start:
            continue
        minutes = (end - start).total_seconds() / 60.0
        samples[end.date().isoformat()].append(
            {"source": str(record.get("sourceName") or ""), "value": minutes}
        )
    for day, group in samples.items():
        chosen = _prefer_watch(group, total=True)
        by_day.setdefault(day, {})["sleep_minutes"] = sum(item["value"] for item in chosen)


def _prefer_watch(samples: list[dict], *, total: bool) -> list[dict]:
    watch = [sample for sample in samples if "watch" in sample["source"].lower()]
    if watch:
        return watch
    by_source: dict[str, list[dict]] = defaultdict(list)
    for sample in samples:
        by_source[sample["source"]].append(sample)
    if len(by_source) <= 1:
        return samples

    def score(group: list[dict]) -> float:
        amounts = [item["value"] for item in group]
        return sum(amounts) if total else float(len(amounts))

    best = max(by_source, key=lambda name: score(by_source[name]))
    return by_source[best]


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S %z")
    except ValueError:
        return None


def _number(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
