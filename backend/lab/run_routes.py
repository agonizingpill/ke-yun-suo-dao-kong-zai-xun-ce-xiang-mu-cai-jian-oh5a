from fastapi import APIRouter
from sqlalchemy import select

from .auth import Current, Db, Technician
from .constants import Shift
from .run_models import WatchRun
from .run_schema import RunEntry
from .run_service import normalize_run, record_run

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
