import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import IssueStatus, UpdateActorType
from app.models.types import enum_type

if TYPE_CHECKING:
    from app.models.issue import Issue


class IssueUpdate(Base):
    __tablename__ = "issue_updates"
    __table_args__ = (Index("ix_issue_updates_timeline", "issue_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    issue_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[IssueStatus | None] = mapped_column(
        enum_type(IssueStatus, "issue_update_from_status"),
    )
    to_status: Mapped[IssueStatus] = mapped_column(
        enum_type(IssueStatus, "issue_update_to_status"),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text)
    actor_type: Mapped[UpdateActorType] = mapped_column(
        enum_type(UpdateActorType, "update_actor_type"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    issue: Mapped["Issue"] = relationship(back_populates="updates")
