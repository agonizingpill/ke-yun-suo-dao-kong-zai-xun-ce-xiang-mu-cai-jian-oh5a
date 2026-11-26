from datetime import date

from pydantic import BaseModel, Field, model_validator

from .constants import Shift


class MarkEntry(BaseModel):
    measure_id: int = Field(gt=0)
    value: float = Field(ge=0, le=10000, allow_inf_nan=False)


class RunEntry(BaseModel):
    series_id: int = Field(gt=0)
    ref: str = Field(min_length=3, max_length=28, pattern=r"^[A-Z0-9-]+$")
    day: date
    shift: Shift
    camera_review: bool
    marks: list[MarkEntry] = Field(min_length=1, max_length=60)

    @model_validator(mode="after")
    def reject_duplicate_marks(self):
        if len(self.marks) != len({m.measure_id for m in self.marks}):
            raise ValueError("同一班次的项目不能重复。")
        return self
