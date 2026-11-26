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
    metrics: Mapped[dict | None] = mapped_column(JSON)
    items: Mapped[list["PanelItem"]] = relationship(lazy="selectin", cascade="all, delete-orphan")


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
