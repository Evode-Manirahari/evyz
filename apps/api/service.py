"""Load one history and remember the label a person attaches to an event."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from core.feedback.labels import feedback_record
from core.pipeline import PipelineConfig, analyze_person
from core.status import event_id, latest_segment, today_status


class HistoryService:
    def __init__(self, daily: pd.DataFrame, feedback_path: Path):
        self.daily = daily
        self.feedback_path = feedback_path
        self._cache: dict[str, list] = {}

    def user_ids(self) -> list[str]:
        return sorted(str(user_id) for user_id in self.daily["user_id"].dropna().unique())

    def status(self, user_id: str, *, selected_event_id: str | None = None) -> dict:
        result = self._latest(user_id)
        saved = self._saved_label(user_id, selected_event_id or _default_event_id(result))
        return today_status(result, selected_event_id=selected_event_id, saved_label=saved)

    def save_feedback(self, *, user_id: str, event_id_value: str, label: str, notes: str | None) -> dict:
        result = self._latest(user_id)
        known = {event_id(event) for event in result.events}
        if event_id_value not in known:
            raise KeyError(event_id_value)
        record = feedback_record(user_id=user_id, event_id=event_id_value, label=label, notes=notes)
        self.feedback_path.parent.mkdir(parents=True, exist_ok=True)
        with self.feedback_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        return record

    def _latest(self, user_id: str):
        if user_id not in self._cache:
            person = self.daily.loc[self.daily["user_id"].astype(str) == user_id]
            if person.empty:
                raise KeyError(user_id)
            self._cache[user_id] = analyze_person(person, PipelineConfig())
        result = latest_segment(self._cache[user_id])
        if result is None:
            raise KeyError(user_id)
        return result

    def _saved_label(self, user_id: str, event_id_value: str | None) -> str | None:
        if not event_id_value or not self.feedback_path.exists():
            return None
        saved = None
        for line in self.feedback_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("user_id") == user_id and record.get("event_id") == event_id_value:
                saved = record.get("label")
        return saved


def _default_event_id(result) -> str | None:
    if not result.events:
        return None
    day = pd.Timestamp(result.features.iloc[-1]["date"]) if result.features is not None else None
    if day is not None:
        for event in result.events:
            if pd.Timestamp(event.start_date) <= day <= pd.Timestamp(event.end_date):
                return event_id(event)
    return event_id(result.events[-1])
