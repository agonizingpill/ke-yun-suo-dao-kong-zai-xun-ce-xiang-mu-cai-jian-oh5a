from fastapi import HTTPException
from sqlalchemy import select

from .audit import record
from .constants import PanelState, TrialState
from .panel_service import panel_by_id
from .run_models import WatchRun
from .trial_models import ShadowTrial


def normalize_trial(row):
    return {"id": row.id, "panel_id": row.panel_id, "run_id": row.run_id, "shift": row.shift,
            "notes": row.notes, "state": row.state, "filed_by": row.filed_by,
            "review_note": row.review_note, "reviewed_by": row.reviewed_by}


def file_trial(db, panel_id, run_id, notes, actor):
    panel = panel_by_id(db, panel_id, lock=True)
    if panel.state != PanelState.TRIAL:
        raise HTTPException(409, "当前面板不在影子试行阶段。")
    run = db.get(WatchRun, run_id)
    if run is None or run.series_id != panel.series_id or run.day <= panel.cutoff_day:
        raise HTTPException(409, "试行须用拟合截止日后的同车型班次记录。")
    measured = {m.measure_id for m in run.marks}
    if any(item.selected and item.measure_id not in measured for item in panel.items):
        raise HTTPException(409, "试行记录缺少面板保留项目。")
    existing = db.scalar(select(ShadowTrial).where(
        ShadowTrial.panel_id == panel_id, ShadowTrial.shift == run.shift,
    ).with_for_update())
    if existing and existing.state != TrialState.RETURNED:
        raise HTTPException(409, "该班次已有待复核或已通过的回执。")
    row = existing or ShadowTrial(panel_id=panel_id, shift=run.shift)
    row.run_id, row.notes, row.filed_by = run_id, notes, actor
    row.state, row.reviewed_by, row.review_note = TrialState.RECORDED, None, None
    db.add(row)
    record(db, actor, "file_shadow_trial", f"{panel.reference}/{run.shift}/{run.ref}")
    db.commit()
    return row


def review_trial(db, trial_id, approve, note, actor):
    trial = db.get(ShadowTrial, trial_id)
    if trial is None:
        raise HTTPException(404, "找不到试行回执。")
    panel = panel_by_id(db, trial.panel_id, lock=True)
    db.refresh(trial, with_for_update=True)
    if panel.state != PanelState.TRIAL or trial.state != TrialState.RECORDED:
        raise HTTPException(409, "仅待复核回执可签。")
    if actor == trial.filed_by:
        raise HTTPException(409, "复核需由独立班长执行。")
    trial.state = TrialState.APPROVED if approve else TrialState.RETURNED
    trial.review_note, trial.reviewed_by = note, actor
    record(db, actor, "trial_" + trial.state, f"{panel.reference}/{trial.shift}")
    db.commit()
    return trial
