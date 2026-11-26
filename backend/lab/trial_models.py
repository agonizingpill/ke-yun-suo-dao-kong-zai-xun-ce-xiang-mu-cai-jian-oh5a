from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class ShadowTrial(Base):
    __tablename__ = "shadow_trials"
    __table_args__ = (
        UniqueConstraint("panel_id", "shift", name="one_trial_per_shift_per_panel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    panel_id: Mapped[int] = mapped_column(ForeignKey("panels.id"))
    run_id: Mapped[int] = mapped_column(ForeignKey("watch_runs.id"))
    shift: Mapped[str] = mapped_column(String(10))
    notes: Mapped[str] = mapped_column(String(300))
    state: Mapped[str] = mapped_column(String(16))
    filed_by: Mapped[str] = mapped_column(String(32))
    reviewed_by: Mapped[str | None] = mapped_column(String(32))
    review_note: Mapped[str | None] = mapped_column(String(220))
