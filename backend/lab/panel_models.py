from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Panel(Base):
    __tablename__ = "panels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"), index=True)
    title: Mapped[str] = mapped_column(String(64))
    reference: Mapped[str] = mapped_column(String(16), unique=True)
    cutoff_day: Mapped[date] = mapped_column(Date)
    budget: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(String(16), index=True)
    requested_by: Mapped[str] = mapped_column(String(32))
    issued_by: Mapped[str | None] = mapped_column(String(32))
    explanation: Mapped[str | None] = mapped_column(String(300))
    invalidation_reason: Mapped[str | None] = mapped_column(String(300))
    metrics: Mapped[dict | None] = mapped_column(JSON)
    items: Mapped[list["PanelItem"]] = relationship(lazy="selectin", cascade="all, delete-orphan")
    samples: Mapped[list["TrainingSample"]] = relationship(lazy="selectin", cascade="all, delete-orphan")


class PanelItem(Base):
    __tablename__ = "panel_items"
    __table_args__ = (
        UniqueConstraint("panel_id", "measure_id", name="one_measure_per_panel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    panel_id: Mapped[int] = mapped_column(ForeignKey("panels.id"))
    measure_id: Mapped[int] = mapped_column(ForeignKey("measures.id"))
    selected: Mapped[bool] = mapped_column(Boolean)
    rank: Mapped[int | None] = mapped_column(Integer)


class TrainingSample(Base):
    """申报时冻结的训练样本与人工复看标签；源数据更正不会改动这里的留档。"""

    __tablename__ = "training_samples"
    __table_args__ = (
        UniqueConstraint("panel_id", "run_id", name="one_sample_claim_per_run"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    panel_id: Mapped[int] = mapped_column(ForeignKey("panels.id"), index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("watch_runs.id"))
    run_ref: Mapped[str] = mapped_column(String(28))
    day: Mapped[date] = mapped_column(Date)
    shift: Mapped[str] = mapped_column(String(10))
    camera_review: Mapped[bool] = mapped_column(Boolean)
    values: Mapped[dict] = mapped_column(JSON)
