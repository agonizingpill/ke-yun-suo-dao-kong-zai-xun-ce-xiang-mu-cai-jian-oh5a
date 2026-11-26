from fastapi import HTTPException
from sqlalchemy import select

from .audit import record
from .catalog import require_series
from .catalog_models import Measure
from .run_models import CheckMark, WatchRun


def normalize_run(row):
    return {"id": row.id, "series_id": row.series_id, "ref": row.ref, "day": row.day.isoformat(),
            "shift": row.shift, "camera_review": row.camera_review, "recorder": row.recorder,
            "marks": [{"measure_id": mark.measure_id, "value": mark.value} for mark in row.marks]}


def record_run(db, body, actor):
    require_series(db, body.series_id)
    book = {row.id: row for row in db.scalars(select(Measure))}
    submitted = {mark.measure_id for mark in body.marks}
    if submitted - book.keys():
        raise HTTPException(422, "存在未登记的巡测项目。")
    protected = [row.label for key, row in book.items() if row.locked and key not in submitted]
    if protected:
        raise HTTPException(409, f"记录缺少锁定项目：{'、'.join(protected)}。")
    row = WatchRun(**body.model_dump(exclude={"marks"}), recorder=actor,
                   marks=[CheckMark(**mark.model_dump()) for mark in body.marks])
    db.add(row)
    record(db, actor, "record_shadow_run", body.ref)
    db.commit()
    return row
