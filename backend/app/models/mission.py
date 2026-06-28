import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.enums import IssueCategory
from app.domain.missions import MissionStatus, MissionType
from app.models.types import enum_type

if TYPE_CHECKING:
    from app.models.area import Area
    from app.models.mission_action import MissionAction


class Mission(TimestampMixin, Base):
    __tablename__ = "missions"
    __table_args__ = (
        CheckConstraint("target_count > 0", name="target_count_positive"),
        CheckConstraint("progress_count >= 0", name="progress_count_non_negative"),
        CheckConstraint("progress_count <= target_count", name="progress_not_above_target"),
        Index("ix_missions_status_expires", "status", "expires_at"),
        Index("ix_missions_area_status", "area_id", "status"),
        Index("ix_missions_type_status", "mission_type", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    area_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("areas.id", ondelete="CASCADE"),
        nullable=False,
    )
    mission_type: Mapped[MissionType] = mapped_column(
        enum_type(MissionType, "mission_type"),
        nullable=False,
    )
    status: Mapped[MissionStatus] = mapped_column(
        enum_type(MissionStatus, "mission_status"),
        default=MissionStatus.DRAFT,
        nullable=False,
    )
    goal_description: Mapped[str] = mapped_column(Text, nullable=False)
    target_count: Mapped[int] = mapped_column(Integer, nullable=False)
    progress_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    category: Mapped[IssueCategory | None] = mapped_column(
        enum_type(IssueCategory, "mission_issue_category"),
    )
    reward_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    ai_reason: Mapped[str] = mapped_column(Text, nullable=False)
    linked_issue_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(120))
    raw_response_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    area: Mapped["Area"] = relationship(back_populates="missions")
    actions: Mapped[list["MissionAction"]] = relationship(
        back_populates="mission",
        cascade="all, delete-orphan",
    )
