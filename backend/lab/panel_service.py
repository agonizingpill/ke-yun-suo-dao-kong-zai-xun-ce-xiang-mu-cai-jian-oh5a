import logging
from uuid import uuid4

from fastapi import HTTPException
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select

from .audit import record
from .catalog import require_series
from .catalog_models import Measure
from .constants import PanelState, Shift, TrialState
from .label_policy import apply_label_correction, snapshot_eligible, snapshot_order
from .panel_models import Panel, PanelItem, TrainingSample
from .rfe_ranker import InadequateSample, fit_rows, snapshot_training_rows
from .run_models import ReviewMarkRevision, WatchRun
from .settings import QUEUE_KEY, REDIS_URL
from .trial_models import ShadowTrial

logger = logging.getLogger("ropeway.panels")


def panel_by_id(db, panel_id, *, lock=False):
    query = select(Panel).where(Panel.id == panel_id)
    panel = db.scalar(query.with_for_update() if lock else query)
    if panel is None:
        raise HTTPException(404, "找不到影子面板。")
    return panel


def _snapshot_rows(db, panel, measures):
    """按与拟合一致的规则选取申报时刻的训练样本并冻结标签。"""
    runs = list(db.scalars(select(WatchRun).where(
        WatchRun.series_id == panel.series_id, WatchRun.day <= panel.cutoff_day,
    )))
    measure_ids = [item.id for item in measures]
    samples = []
    for run in snapshot_order(runs):
        by_id = {mark.measure_id: mark.value for mark in run.marks}
        if not snapshot_eligible({"id": run.id, "marks": by_id}, measure_ids):
            continue
        samples.append(TrainingSample(
            panel_id=panel.id, run_id=run.id, run_ref=run.ref, day=run.day, shift=run.shift,
            camera_review=run.camera_review, values={str(item): by_id[item] for item in measure_ids},
        ))
    return samples


def normalize_panel(row):
    return {"id": row.id, "series_id": row.series_id, "reference": row.reference, "title": row.title,
            "cutoff_day": row.cutoff_day.isoformat(), "budget": row.budget, "state": row.state,
            "requested_by": row.requested_by, "issued_by": row.issued_by, "explanation": row.explanation,
            "invalidation_reason": row.invalidation_reason,
            "metrics": row.metrics,
            "items": [{"id": item.measure_id, "selected": item.selected, "rank": item.rank}
                      for item in row.items],
            "training_samples": [
                {"run_id": sample.run_id, "run_ref": sample.run_ref, "day": sample.day.isoformat(),
                 "shift": sample.shift, "camera_review": sample.camera_review}
                for sample in row.samples]}


def submit_candidate(db, form, actor):
    require_series(db, form.series_id, lock=True)
    available = len(list(db.scalars(select(Measure.id).where(Measure.locked.is_(False)))))
    if form.budget >= available:
        raise HTTPException(409, f"自选项预算须少于现有 {available} 项，不含任何锁定项目。")
    panel = Panel(**form.model_dump(), reference="RP-" + uuid4().hex[:10].upper(),
                  state=PanelState.QUEUED, requested_by=actor)
    db.add(panel)
    db.flush()
    measures = list(db.scalars(select(Measure).order_by(Measure.id)))
    panel.samples.extend(_snapshot_rows(db, panel, measures))
    record(db, actor, "request_panel",
           f"{panel.reference}/samples={len(panel.samples)}")
    db.commit()
    try:
        Redis.from_url(REDIS_URL, socket_timeout=3, socket_connect_timeout=2).lpush(QUEUE_KEY, panel.id)
    except RedisError:
        logger.warning("Redis delayed; DB candidate available: %s", panel.reference)
    return panel


def invalidate_for_label_change(db, run, actor, previous_value, current_value, reason):
    """源复看标签更正：未签发且用过该记录做训练依据的候选一律失效。

    判定规则在 label_policy 内可独立测试；这里负责加锁取数、写状态和审计。
    """
    rows = list(db.scalars(select(Panel).join(
        TrainingSample, TrainingSample.panel_id == Panel.id,
    ).where(
        TrainingSample.run_id == run.id,
    ).order_by(Panel.id).with_for_update(skip_locked=True)))
    candidates = list(rows)
    sample_rows = list(db.scalars(select(TrainingSample).where(
        TrainingSample.panel_id.in_([panel.id for panel in candidates]),
    )))
    sample_run_ids = {}
    for sample in sample_rows:
        sample_run_ids.setdefault(sample.panel_id, set()).add(sample.run_id)
    affected = apply_label_correction(
        candidates, sample_run_ids, run.id, run.ref, actor,
        previous_value, current_value, reason,
    )
    for panel in affected:
        record(db, actor, "invalidate_panel", panel.reference)
    return affected


def process_pending(db):
    ticket = db.scalar(select(Panel).where(Panel.state == PanelState.QUEUED).order_by(Panel.id)
                       .limit(1).with_for_update(skip_locked=True))
    if ticket is None:
        return False
    measures = list(db.scalars(select(Measure).order_by(Measure.id)))
    optional = [item for item in measures if not item.locked]
    # 锁定快照对应的源班次记录：拟合期间任何标签更正都会等待本事务结束，
    # 更正随后看到的已是 trial 面板并将其失效，避免漏判。
    sample_run_ids = sorted({sample.run_id for sample in ticket.samples})
    if sample_run_ids:
        list(db.scalars(select(WatchRun).where(WatchRun.id.in_(sample_run_ids))
                        .order_by(WatchRun.id).with_for_update()))
    # 并发窗口兜底：若更正事务因行锁跳过了本候选，其提交的修订在这里可见，
    # 候选直接判失效，不能带着过期标签进入试行。
    revised = db.scalar(select(ReviewMarkRevision.id).where(
        ReviewMarkRevision.run_id.in_(sample_run_ids),
    ).limit(1)) if sample_run_ids else None
    if revised is not None:
        ticket.state = PanelState.INVALID
        ticket.invalidation_reason = "排队拟合期间训练依据的人工复看标签已被更正，冻结样本过期，须重新申报。"
        record(db, "worker", "rank_invalid", ticket.reference)
        db.commit()
        return True
    rows = snapshot_training_rows(ticket.samples, measures)
    try:
        ranking, ticket.metrics = fit_rows(rows, [item.id for item in measures], ticket.budget)
    except InadequateSample as exc:
        ticket.state, ticket.explanation = PanelState.REJECTED, str(exc)
    else:
        for item in measures:
            if item.locked:
                ticket.items.append(PanelItem(measure_id=item.id, selected=True, rank=None))
            else:
                keep, rank = ranking[item.id]
                ticket.items.append(PanelItem(measure_id=item.id, selected=keep, rank=rank))
        if ticket.metrics["full_score"] - ticket.metrics["compact_score"] > 0.15:
            ticket.state = PanelState.REJECTED
            ticket.explanation = "自选项精简后，按日期留组平衡准确率下降超过 0.15。"
        else:
            ticket.state = PanelState.TRIAL
            ticket.explanation = "允许并行影子试行。线上登记规则保持完整。"
    record(db, "worker", "rank_" + ticket.state, ticket.reference)
    db.commit()
    return True


def issue_panel(db, panel_id, actor, confirmed):
    panel = panel_by_id(db, panel_id)
    series = require_series(db, panel.series_id, lock=True)
    db.refresh(panel, with_for_update=True)
    if panel.state == PanelState.INVALID:
        raise HTTPException(409, "该候选的训练标签已被更正而失效，禁止签发，请重新申报后复核早晚班。")
    if panel.state != PanelState.TRIAL:
        raise HTTPException(409, "只有通过拟合的影子试行单可签发。")
    if not confirmed or actor == panel.requested_by:
        raise HTTPException(409, "班长需确认独立签发和影子用途。")
    entries = list(db.scalars(select(ShadowTrial).where(
        ShadowTrial.panel_id == panel.id, ShadowTrial.state == TrialState.APPROVED,
    )))
    if {row.shift for row in entries} != {Shift.DAWN, Shift.DUSK}:
        raise HTTPException(409, "早班和晚班试行回执都须复核通过。")
    locked = set(db.scalars(select(Measure.id).where(Measure.locked.is_(True))))
    if locked.difference(item.measure_id for item in panel.items if item.selected and item.rank is None):
        raise HTTPException(409, "面板遗漏锁定项目，禁止签发。")
    if series.current_panel_id is not None:
        previous = panel_by_id(db, series.current_panel_id, lock=True)
        previous.state = PanelState.ARCHIVED
    panel.state, panel.issued_by = PanelState.ISSUED, actor
    series.current_panel_id = panel.id
    record(db, actor, "issue_shadow_panel",
           f"{panel.reference}/samples={len(panel.samples)}/sha256={panel.metrics['input_sha256'] if panel.metrics else '-'}")
    db.commit()
    return panel
