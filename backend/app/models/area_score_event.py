import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.areas import AreaScoreKey
from app.models.types import enum_type

if TYPE_CHECKING:
    from app.models.area import Area


class AreaScoreEvent(Base):
    __tablename__ = "area_score_events"
    __table_args__ = (
        Index("ix_area_score_events_area_created", "area_id", "created_at"),
        Index("ix_area_score_events_score_key", "score_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    area_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("areas.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    related_issue_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("issues.id", ondelete="SET NULL"),
    )
    related_mission_id: Mapped[uuid.UUID | None] = mapped_column()
    score_key: Mapped[AreaScoreKey] = mapped_column(
        enum_type(AreaScoreKey, "area_score_key"),
        nullable=False,
    )
    score_change: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_score: Mapped[int] = mapped_column(Integer, nullable=False)
    new_score: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    area: Mapped["Area"] = relationship(back_populates="score_events")
