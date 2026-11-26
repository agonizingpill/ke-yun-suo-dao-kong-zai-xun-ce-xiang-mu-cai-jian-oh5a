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
from .panel_models import Panel, PanelItem
from .rfe_ranker import InadequateSample, fit_optional
from .run_models import WatchRun
from .settings import QUEUE_KEY, REDIS_URL
from .trial_models import ShadowTrial

logger = logging.getLogger("ropeway.panels")


def panel_by_id(db, panel_id, *, lock=False):
    query = select(Panel).where(Panel.id == panel_id)
    panel = db.scalar(query.with_for_update() if lock else query)
    if panel is None:
        raise HTTPException(404, "找不到影子面板。")
    return panel


def normalize_panel(row):
    return {"id": row.id, "series_id": row.series_id, "reference": row.reference, "title": row.title,
            "cutoff_day": row.cutoff_day.isoformat(), "budget": row.budget, "state": row.state,
            "requested_by": row.requested_by, "issued_by": row.issued_by, "explanation": row.explanation,
            "metrics": row.metrics, "items": [{"id": item.measure_id, "selected": item.selected, "rank": item.rank}
                                              for item in row.items]}


def submit_candidate(db, form, actor):
    require_series(db, form.series_id, lock=True)
    available = len(list(db.scalars(select(Measure.id).where(Measure.locked.is_(False)))))
    if form.budget >= available:
        raise HTTPException(409, f"自选项预算须少于现有 {available} 项，不含任何锁定项目。")
    panel = Panel(**form.model_dump(), reference="RP-" + uuid4().hex[:10].upper(),
                  state=PanelState.QUEUED, requested_by=actor)
    db.add(panel)
    record(db, actor, "request_panel", panel.reference)
    db.commit()
    try:
        Redis.from_url(REDIS_URL, socket_timeout=3, socket_connect_timeout=2).lpush(QUEUE_KEY, panel.id)
    except RedisError:
        logger.warning("Redis delayed; DB candidate available: %s", panel.reference)
    return panel


def process_pending(db):
    ticket = db.scalar(select(Panel).where(Panel.state == PanelState.QUEUED).order_by(Panel.id)
                       .limit(1).with_for_update(skip_locked=True))
    if ticket is None:
        return False
    measures = list(db.scalars(select(Measure).order_by(Measure.id)))
    optional = [item for item in measures if not item.locked]
    runs = list(db.scalars(select(WatchRun).where(
        WatchRun.series_id == ticket.series_id, WatchRun.day <= ticket.cutoff_day,
    ).order_by(WatchRun.day, WatchRun.id)))
    try:
        ranking, ticket.metrics = fit_optional(runs, optional, ticket.budget)
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
    record(db, actor, "issue_shadow_panel", panel.reference)
    db.commit()
    return panel
