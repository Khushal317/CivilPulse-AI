import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.missions import MissionActionType
from app.models.types import enum_type

if TYPE_CHECKING:
    from app.models.issue import Issue
    from app.models.mission import Mission


class MissionAction(Base):
    __tablename__ = "mission_actions"
    __table_args__ = (
        Index(
            "uq_mission_actions_issue_actor",
            "mission_id",
            "issue_id",
            "action_type",
            "actor_hash",
            unique=True,
            sqlite_where=text("issue_id IS NOT NULL"),
            postgresql_where=text("issue_id IS NOT NULL"),
        ),
        Index(
            "uq_mission_actions_global_actor",
            "mission_id",
            "action_type",
            "actor_hash",
            unique=True,
            sqlite_where=text("issue_id IS NULL"),
            postgresql_where=text("issue_id IS NULL"),
        ),
        Index("ix_mission_actions_mission_type", "mission_id", "action_type"),
        Index("ix_mission_actions_actor_created", "actor_hash", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    mission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=False,
    )
    issue_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("issues.id", ondelete="SET NULL"),
    )
    action_type: Mapped[MissionActionType] = mapped_column(
        enum_type(MissionActionType, "mission_action_type"),
        nullable=False,
    )
    actor_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    mission: Mapped["Mission"] = relationship(back_populates="actions")
    issue: Mapped["Issue | None"] = relationship()
