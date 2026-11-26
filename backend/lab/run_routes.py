from fastapi import APIRouter
from sqlalchemy import select

from .auth import Current, Db, Technician
from .constants import Shift
from .run_models import WatchRun
from .run_schema import ReviewMarkCorrection, RunEntry
from .run_service import correct_review_mark, normalize_run, record_run

router = APIRouter(prefix="/runs", tags=["班次记录"])


@router.get("")
def runs(db: Db, _operator: Current, series_id: int | None = None, shift: Shift | None = None):
    query = select(WatchRun).order_by(WatchRun.day.desc(), WatchRun.id.desc())
    if series_id:
        query = query.where(WatchRun.series_id == series_id)
    if shift:
        query = query.where(WatchRun.shift == shift)
    return [normalize_run(row) for row in db.scalars(query.limit(200))]


@router.post("", status_code=201)
def add(body: RunEntry, db: Db, operator: Technician):
    return normalize_run(record_run(db, body, operator.username))


@router.patch("/{run_id}/review-mark")
def correct(run_id: int, body: ReviewMarkCorrection, db: Db, operator: Technician):
    run, invalidated = correct_review_mark(
        db, run_id, body.camera_review, body.reason.strip(), operator.username,
    )
    return {"run": normalize_run(run),
            "invalidated_panels": [{"id": panel.id, "reference": panel.reference} for panel in invalidated]}
