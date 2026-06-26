import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import CommunityActionType
from app.models.types import enum_type

if TYPE_CHECKING:
    from app.models.issue import Issue


class CommunityAction(Base):
    __tablename__ = "community_actions"
    __table_args__ = (
        UniqueConstraint(
            "issue_id",
            "action_type",
            "actor_hash",
            name="uq_community_actions_issue_action_actor",
        ),
        Index("ix_community_actions_issue_type", "issue_id", "action_type"),
        Index("ix_community_actions_actor_created", "actor_hash", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    issue_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
    )
    action_type: Mapped[CommunityActionType] = mapped_column(
        enum_type(CommunityActionType, "community_action_type"),
        nullable=False,
    )
    actor_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    issue: Mapped["Issue"] = relationship(back_populates="community_actions")
