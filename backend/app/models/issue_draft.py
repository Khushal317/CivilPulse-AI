import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.domain.enums import IssueCategory, IssueSeverity, UrgencyLevel
from app.models.types import enum_type


class IssueDraft(TimestampMixin, Base):
    __tablename__ = "issue_drafts"
    __table_args__ = (Index("ix_issue_drafts_expires_unpublished", "expires_at", "published_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    original_description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    landmark: Mapped[str | None] = mapped_column(String(255))
    citizen_name: Mapped[str | None] = mapped_column(String(120))
    citizen_contact: Mapped[str | None] = mapped_column(String(255))
    urgency_note: Mapped[str | None] = mapped_column(Text)
    image_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    image_mime: Mapped[str] = mapped_column(String(50), nullable=False)

    title: Mapped[str | None] = mapped_column(String(180))
    ai_summary: Mapped[str | None] = mapped_column(Text)
    category: Mapped[IssueCategory | None] = mapped_column(
        enum_type(IssueCategory, "issue_category"),
    )
    severity: Mapped[IssueSeverity | None] = mapped_column(
        enum_type(IssueSeverity, "issue_severity"),
    )
    urgency_level: Mapped[UrgencyLevel | None] = mapped_column(
        enum_type(UrgencyLevel, "urgency_level"),
    )
    urgency_reason: Mapped[str | None] = mapped_column(Text)
    suggested_department: Mapped[str | None] = mapped_column(String(180))
    safety_risk: Mapped[str | None] = mapped_column(Text)
    citizen_explanation: Mapped[str | None] = mapped_column(Text)
    suggested_next_action: Mapped[str | None] = mapped_column(Text)
    ai_model: Mapped[str | None] = mapped_column(String(120))
    prompt_version: Mapped[str | None] = mapped_column(String(50))

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
