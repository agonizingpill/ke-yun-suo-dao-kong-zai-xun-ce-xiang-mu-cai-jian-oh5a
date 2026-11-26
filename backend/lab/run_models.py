from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class WatchRun(Base):
    __tablename__ = "watch_runs"
    __table_args__ = (
        CheckConstraint("shift IN ('dawn','dusk')", name="watch_shift_known"),
        UniqueConstraint("series_id", "ref", name="unique_shadow_watch_run"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), index=True)
    ref: Mapped[str] = mapped_column(String(28))
    day: Mapped[date] = mapped_column(Date, index=True)
    shift: Mapped[str] = mapped_column(String(10))
    camera_review: Mapped[bool] = mapped_column(Boolean)
    recorder: Mapped[str] = mapped_column(String(32))
    marks: Mapped[list["CheckMark"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class CheckMark(Base):
    __tablename__ = "check_marks"
    __table_args__ = (
        UniqueConstraint("run_id", "measure_id", name="one_value_per_run"),
        CheckConstraint("value BETWEEN 0 AND 10000", name="valid_watch_measure_value"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("watch_runs.id"))
    measure_id: Mapped[int] = mapped_column(ForeignKey("measures.id"))
    value: Mapped[float] = mapped_column(Float)
