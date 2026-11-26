from fastapi import HTTPException
from sqlalchemy import select

from .audit import record
from .catalog import require_series
from .catalog_models import Measure
from .panel_service import invalidate_for_label_change
from .run_models import CheckMark, ReviewMarkRevision, WatchRun


def _normalize_revision(row):
    return {"id": row.id, "previous_value": row.previous_value, "current_value": row.current_value,
            "reason": row.reason, "revised_by": row.revised_by,
            "revised_at": row.revised_at.isoformat() if row.revised_at else None}


def normalize_run(row):
    return {"id": row.id, "series_id": row.series_id, "ref": row.ref, "day": row.day.isoformat(),
            "shift": row.shift, "camera_review": row.camera_review, "recorder": row.recorder,
            "revised": bool(row.revisions),
            "revisions": [_normalize_revision(item) for item in row.revisions],
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


def correct_review_mark(db, run_id, camera_review, reason, actor):
    run = db.scalar(select(WatchRun).where(WatchRun.id == run_id).with_for_update())
    if run is None:
        raise HTTPException(404, "找不到班次记录。")
    if run.camera_review == camera_review:
        raise HTTPException(409, "更正后的人工复看标签与现值相同，无需更正。")
    previous = run.camera_review
    run.camera_review = camera_review
    revision = ReviewMarkRevision(run_id=run.id, previous_value=previous, current_value=camera_review,
                                  reason=reason, revised_by=actor)
    db.add(revision)
    db.flush()
    invalidated = invalidate_for_label_change(
        db, run, actor, previous, camera_review, reason,
    )
    record(db, actor, "correct_review_mark",
           f"{run.ref}/{int(previous)}>{int(camera_review)}/invalid={len(invalidated)}")
    db.commit()
    return run, invalidated
