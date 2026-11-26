from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from .auth import Current, Db
from .catalog_models import Measure, Series

router = APIRouter(prefix="/catalog", tags=["巡测项目"])


def require_series(db, series_id, *, lock=False):
    query = select(Series).where(Series.id == series_id)
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise HTTPException(404, "找不到车型台账。")
    return row


@router.get("")
def catalog(db: Db, _operator: Current):
    series = db.scalars(select(Series).order_by(Series.code))
    measures = db.scalars(select(Measure).order_by(Measure.locked.desc(), Measure.code))
    return {
        "series": [{"id": row.id, "code": row.code, "label": row.label, "current_panel_id": row.current_panel_id}
                   for row in series],
        "measures": [{"id": row.id, "code": row.code, "label": row.label, "unit": row.unit,
                      "source": row.source, "locked": row.locked} for row in measures],
    }
