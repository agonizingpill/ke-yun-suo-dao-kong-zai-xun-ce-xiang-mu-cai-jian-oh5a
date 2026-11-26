from fastapi import APIRouter
from sqlalchemy import select

from .auth import Current, Db, Supervisor, Technician
from .panel_models import Panel
from .panel_schema import CandidateForm, IssueForm
from .panel_service import issue_panel, normalize_panel, panel_by_id, submit_candidate

router = APIRouter(prefix="/panels", tags=["影子面板"])


@router.get("")
def panels(db: Db, _operator: Current):
    return [normalize_panel(row) for row in db.scalars(select(Panel).order_by(Panel.id.desc()).limit(80))]


@router.get("/{panel_id}")
def panel(panel_id: int, db: Db, _operator: Current):
    return normalize_panel(panel_by_id(db, panel_id))


@router.post("", status_code=202)
def candidate(form: CandidateForm, db: Db, operator: Technician):
    return normalize_panel(submit_candidate(db, form, operator.username))


@router.post("/{panel_id}/issue")
def issue(panel_id: int, form: IssueForm, db: Db, operator: Supervisor):
    return normalize_panel(issue_panel(db, panel_id, operator.username, form.confirm_shadow))
