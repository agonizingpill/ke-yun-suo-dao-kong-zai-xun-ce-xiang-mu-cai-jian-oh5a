import json

from sqlalchemy import func, select

from lab.auth import hash_password
from lab.catalog_models import Measure, Series
from lab.constants import PanelState
from lab.database import initialize, open_session
from lab.identity_models import Operator
from lab.panel_models import Panel, PanelItem
from lab.run_models import CheckMark, WatchRun
from lab.settings import DEMO_PASSWORD
from lab.trial_models import ShadowTrial

from .shadow_fixtures import CREW, CUTOFF, MEASURES, historical_runs


def seed():
    with open_session() as db:
        for username, display_name, role in CREW:
            if db.scalar(select(Operator).where(Operator.username == username)) is None:
                db.add(Operator(username=username, display_name=display_name, role=role,
                                password_digest=hash_password(DEMO_PASSWORD)))
        catalog = []
        for code, label, unit, source, locked in MEASURES:
            row = db.scalar(select(Measure).where(Measure.code == code))
            if row is None:
                row = Measure(code=code, label=label, unit=unit, source=source, locked=locked)
                db.add(row)
            catalog.append(row)
        series = db.scalar(select(Series).where(Series.code == "Y7"))
        if series is None:
            series = Series(code="Y7", label="云脊七号 · 空载影子线路")
            db.add(series)
        if db.scalar(select(Series).where(Series.code == "X3")) is None:
            db.add(Series(code="X3", label="霞岭三号 · 样本待积累"))
        db.flush()
        refs = set(db.scalars(select(WatchRun.ref).where(WatchRun.series_id == series.id)))
        for attrs, values in historical_runs():
            if attrs["ref"] in refs:
                continue
            db.add(WatchRun(series_id=series.id, recorder="duan", **attrs,
                            marks=[CheckMark(measure_id=item.id, value=value)
                                   for item, value in zip(catalog, values, strict=True)]))
        if series.current_panel_id is None and db.scalar(select(Panel).where(Panel.reference == "RP-DEMO-Y7")) is None:
            panel = Panel(series_id=series.id, reference="RP-DEMO-Y7", title="并行观察 · 全目录旧版",
                          cutoff_day=CUTOFF, budget=6, state=PanelState.ISSUED, requested_by="duan", issued_by="ning",
                          explanation="演示旧版保留全部项目，等待完成双班试行后替换。",
                          items=[PanelItem(measure_id=item.id, selected=True) for item in catalog])
            db.add(panel)
            db.flush()
            series.current_panel_id = panel.id
        db.commit()
        tracked = (Operator, Measure, Series, WatchRun, CheckMark, Panel, PanelItem, ShadowTrial)
        return {m.__tablename__: db.scalar(select(func.count()).select_from(m)) for m in tracked}


if __name__ == "__main__":
    initialize()
    print(json.dumps(seed(), sort_keys=True))
