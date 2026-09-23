"""Serve today's status for one WearableQA history."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from apps.api.service import HistoryService
from core.normalization.wearableqa import load_wearableqa

ROOT = Path(__file__).resolve().parents[2]
PAGE = Path(__file__).resolve().parent / "static" / "index.html"
DEFAULT_USER = "user_131"


class FeedbackIn(BaseModel):
    user_id: str
    event_id: str
    label: str
    notes: str | None = Field(default=None, max_length=500)


def create_app(service: HistoryService | None = None, data_path: Path | None = None) -> FastAPI:
    app = FastAPI(title="EVYZ")
    app.state.service = service
    app.state.data_path = data_path or Path(os.environ.get("EVYZ_DATA_DIR", ROOT / "data" / "raw" / "wearableqa"))
    app.state.feedback_path = ROOT / "data" / "processed" / "feedback.jsonl"

    @app.get("/")
    def home():
        return FileResponse(PAGE)

    @app.get("/api/status")
    def status(user: str = DEFAULT_USER, event: str | None = None):
        try:
            return _service(app).status(user, selected_event_id=event)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"No history for {user}.") from None
        except FileNotFoundError as error:
            raise HTTPException(status_code=503, detail=str(error)) from None

    @app.post("/api/feedback")
    def feedback(body: FeedbackIn):
        try:
            return _service(app).save_feedback(
                user_id=body.user_id,
                event_id_value=body.event_id,
                label=body.label,
                notes=body.notes,
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="That event is not on this history.") from None
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from None

    return app


def _service(app: FastAPI) -> HistoryService:
    if app.state.service is not None:
        return app.state.service
    path = Path(app.state.data_path)
    parquet = path / "structured.parquet" if path.is_dir() else path
    if not parquet.exists():
        raise FileNotFoundError(f"Dataset not found at {parquet}. Run scripts/download_wearableqa.py first.")
    daily = load_wearableqa(parquet)
    app.state.service = HistoryService(daily, Path(app.state.feedback_path))
    return app.state.service


app = create_app()
