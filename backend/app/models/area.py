import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.domain.areas import BASELINE_AREA_SCORE, DEFAULT_AREA_CITY

if TYPE_CHECKING:
    from app.models.area_score_event import AreaScoreEvent
    from app.models.issue import Issue
    from app.models.mission import Mission


class Area(TimestampMixin, Base):
    __tablename__ = "areas"
    __table_args__ = (
        UniqueConstraint("city", "slug", name="uq_areas_city_slug"),
        CheckConstraint("overall_score >= 0 AND overall_score <= 100", name="overall_score_range"),
        CheckConstraint(
            "infrastructure_score >= 0 AND infrastructure_score <= 100",
            name="infrastructure_score_range",
        ),
        CheckConstraint(
            "cleanliness_score >= 0 AND cleanliness_score <= 100",
            name="cleanliness_score_range",
        ),
        CheckConstraint("safety_score >= 0 AND safety_score <= 100", name="safety_score_range"),
        CheckConstraint(
            "participation_score >= 0 AND participation_score <= 100",
            name="participation_score_range",
        ),
        CheckConstraint(
            "responsiveness_score >= 0 AND responsiveness_score <= 100",
            name="responsiveness_score_range",
        ),
        CheckConstraint(
            "environment_score >= 0 AND environment_score <= 100",
            name="environment_score_range",
        ),
        Index("ix_areas_rank", "rank"),
        Index("ix_areas_overall_score", "overall_score"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False)
    city: Mapped[str] = mapped_column(String(120), default=DEFAULT_AREA_CITY, nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, default=BASELINE_AREA_SCORE, nullable=False)
    infrastructure_score: Mapped[int] = mapped_column(
        Integer,
        default=BASELINE_AREA_SCORE,
        nullable=False,
    )
    cleanliness_score: Mapped[int] = mapped_column(
        Integer,
        default=BASELINE_AREA_SCORE,
        nullable=False,
    )
    safety_score: Mapped[int] = mapped_column(Integer, default=BASELINE_AREA_SCORE, nullable=False)
    participation_score: Mapped[int] = mapped_column(
        Integer,
        default=BASELINE_AREA_SCORE,
        nullable=False,
    )
    responsiveness_score: Mapped[int] = mapped_column(
        Integer,
        default=BASELINE_AREA_SCORE,
        nullable=False,
    )
    environment_score: Mapped[int] = mapped_column(
        Integer,
        default=BASELINE_AREA_SCORE,
        nullable=False,
    )
    rank: Mapped[int | None] = mapped_column(Integer)
    status_label: Mapped[str] = mapped_column(String(40), default="improving", nullable=False)

    issues: Mapped[list["Issue"]] = relationship(back_populates="area")
    missions: Mapped[list["Mission"]] = relationship(back_populates="area")
    score_events: Mapped[list["AreaScoreEvent"]] = relationship(
        back_populates="area",
        cascade="all, delete-orphan",
        order_by="AreaScoreEvent.created_at.desc()",
    )
