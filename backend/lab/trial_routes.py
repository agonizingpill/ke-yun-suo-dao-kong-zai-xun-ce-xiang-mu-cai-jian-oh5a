from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from .auth import Current, Db, Supervisor, Technician
from .trial_models import ShadowTrial
from .trial_service import file_trial, normalize_trial, review_trial

router = APIRouter(prefix="/trials", tags=["双班试行"])


class TrialForm(BaseModel):
    panel_id: int = Field(gt=0)
    run_id: int = Field(gt=0)
    notes: str = Field(min_length=6, max_length=300)


class ReviewForm(BaseModel):
    approve: bool
    note: str = Field(min_length=4, max_length=220)


@router.get("")
def history(db: Db, _operator: Current, panel_id: int | None = None):
    query = select(ShadowTrial).order_by(ShadowTrial.id.desc())
    if panel_id is not None:
        query = query.where(ShadowTrial.panel_id == panel_id)
    return [normalize_trial(row) for row in db.scalars(query.limit(200))]


@router.post("", status_code=201)
def record(form: TrialForm, db: Db, operator: Technician):
    return normalize_trial(file_trial(db, form.panel_id, form.run_id, form.notes, operator.username))


@router.post("/{trial_id}/review")
def review(trial_id: int, form: ReviewForm, db: Db, operator: Supervisor):
    return normalize_trial(review_trial(db, trial_id, form.approve, form.note, operator.username))
