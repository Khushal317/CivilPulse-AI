import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.enums import IssueCategory, IssueSeverity, IssueStatus, UrgencyLevel
from app.models.types import enum_type

if TYPE_CHECKING:
    from app.models.community_action import CommunityAction
    from app.models.issue_update import IssueUpdate


class Issue(TimestampMixin, Base):
    __tablename__ = "issues"
    __table_args__ = (
        Index("ix_issues_tracker_newest", "status", "created_at"),
        Index("ix_issues_category_severity", "category", "severity"),
        Index("ix_issues_location_search", "location"),
        Index("ix_issues_admin_updated", "updated_at", "id"),
        Index("ix_issues_priority_queue", "severity", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    public_reference: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    original_description: Mapped[str] = mapped_column(Text, nullable=False)
    ai_summary: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[IssueCategory] = mapped_column(
        enum_type(IssueCategory, "issue_category"),
        nullable=False,
    )
    severity: Mapped[IssueSeverity] = mapped_column(
        enum_type(IssueSeverity, "issue_severity"),
        nullable=False,
    )
    urgency_level: Mapped[UrgencyLevel] = mapped_column(
        enum_type(UrgencyLevel, "urgency_level"),
        nullable=False,
    )
    urgency_reason: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_department: Mapped[str] = mapped_column(String(180), nullable=False)
    safety_risk: Mapped[str] = mapped_column(Text, nullable=False)
    citizen_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_next_action: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    landmark: Mapped[str | None] = mapped_column(String(255))
    image_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    image_mime: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[IssueStatus] = mapped_column(
        enum_type(IssueStatus, "issue_status"),
        default=IssueStatus.REPORTED,
        nullable=False,
    )
    citizen_name: Mapped[str | None] = mapped_column(String(120))
    citizen_contact: Mapped[str | None] = mapped_column(String(255))
    ai_model: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)

    updates: Mapped[list["IssueUpdate"]] = relationship(
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="IssueUpdate.created_at",
    )
    community_actions: Mapped[list["CommunityAction"]] = relationship(
        back_populates="issue",
        cascade="all, delete-orphan",
    )
