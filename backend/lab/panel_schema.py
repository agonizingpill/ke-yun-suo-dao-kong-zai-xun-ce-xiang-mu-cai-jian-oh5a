from datetime import date

from pydantic import BaseModel, Field


class CandidateForm(BaseModel):
    series_id: int = Field(gt=0)
    title: str = Field(min_length=4, max_length=64)
    cutoff_day: date
    budget: int = Field(ge=1, le=12)


class IssueForm(BaseModel):
    confirm_shadow: bool
