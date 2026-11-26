from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Series(Base):
    __tablename__ = "series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(12), unique=True)
    label: Mapped[str] = mapped_column(String(80))
    current_panel_id: Mapped[int | None] = mapped_column(ForeignKey("panels.id", use_alter=True, name="series_current_panel_fk"))


class Measure(Base):
    __tablename__ = "measures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    label: Mapped[str] = mapped_column(String(80))
    unit: Mapped[str] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(120))
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False)
