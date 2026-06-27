"""Add canonical civic areas.

Revision ID: 20260627_05
Revises: 20260626_04
Create Date: 2026-06-27
"""

import re
import unicodedata
import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

revision: str = "20260627_05"
down_revision: str | None = "20260626_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_CITY = "CivicPulse City"
BASELINE_SCORE = 70


def _normalize_area_name(value: str) -> str:
    collapsed = " ".join(value.strip().split())
    return collapsed[:255] if collapsed else "Unknown Area"


def _area_slug(name: str, city: str = DEFAULT_CITY) -> str:
    source = f"{city} {name}"
    ascii_text = (
        unicodedata.normalize("NFKD", source)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    return slug[:180] or "unknown-area"


def upgrade() -> None:
    op.create_table(
        "areas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("infrastructure_score", sa.Integer(), nullable=False),
        sa.Column("cleanliness_score", sa.Integer(), nullable=False),
        sa.Column("safety_score", sa.Integer(), nullable=False),
        sa.Column("participation_score", sa.Integer(), nullable=False),
        sa.Column("responsiveness_score", sa.Integer(), nullable=False),
        sa.Column("environment_score", sa.Integer(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("status_label", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "overall_score >= 0 AND overall_score <= 100",
            name="ck_areas_overall_score_range",
        ),
        sa.CheckConstraint(
            "infrastructure_score >= 0 AND infrastructure_score <= 100",
            name="ck_areas_infrastructure_score_range",
        ),
        sa.CheckConstraint(
            "cleanliness_score >= 0 AND cleanliness_score <= 100",
            name="ck_areas_cleanliness_score_range",
        ),
        sa.CheckConstraint(
            "safety_score >= 0 AND safety_score <= 100",
            name="ck_areas_safety_score_range",
        ),
        sa.CheckConstraint(
            "participation_score >= 0 AND participation_score <= 100",
            name="ck_areas_participation_score_range",
        ),
        sa.CheckConstraint(
            "responsiveness_score >= 0 AND responsiveness_score <= 100",
            name="ck_areas_responsiveness_score_range",
        ),
        sa.CheckConstraint(
            "environment_score >= 0 AND environment_score <= 100",
            name="ck_areas_environment_score_range",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_areas"),
        sa.UniqueConstraint("city", "slug", name="uq_areas_city_slug"),
    )
    op.create_index("ix_areas_overall_score", "areas", ["overall_score"], unique=False)
    op.create_index("ix_areas_rank", "areas", ["rank"], unique=False)
    op.add_column("issues", sa.Column("area_id", sa.Uuid(), nullable=True))
    op.create_index("ix_issues_area_status", "issues", ["area_id", "status"], unique=False)
    op.create_foreign_key(
        "fk_issues_area_id_areas",
        "issues",
        "areas",
        ["area_id"],
        ["id"],
        ondelete="SET NULL",
    )

    if not context.is_offline_mode():
        _backfill_issue_areas()


def _backfill_issue_areas() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT DISTINCT location FROM issues WHERE location IS NOT NULL"),
    ).all()
    area_ids_by_slug: dict[str, uuid.UUID] = {}
    for (location,) in rows:
        name = _normalize_area_name(str(location))
        slug = _area_slug(name)
        area_id = area_ids_by_slug.get(slug)
        if area_id is None:
            area_id = uuid.uuid4()
            area_ids_by_slug[slug] = area_id
            connection.execute(
                sa.text(
                    """
                    INSERT INTO areas (
                        id,
                        name,
                        slug,
                        city,
                        overall_score,
                        infrastructure_score,
                        cleanliness_score,
                        safety_score,
                        participation_score,
                        responsiveness_score,
                        environment_score,
                        rank,
                        status_label
                    )
                    VALUES (
                        :id,
                        :name,
                        :slug,
                        :city,
                        :score,
                        :score,
                        :score,
                        :score,
                        :score,
                        :score,
                        :score,
                        NULL,
                        'improving'
                    )
                    """
                ),
                {
                    "id": area_id,
                    "name": name,
                    "slug": slug,
                    "city": DEFAULT_CITY,
                    "score": BASELINE_SCORE,
                },
            )
        connection.execute(
            sa.text("UPDATE issues SET area_id = :area_id WHERE location = :location"),
            {"area_id": area_id, "location": location},
        )


def downgrade() -> None:
    op.drop_constraint("fk_issues_area_id_areas", "issues", type_="foreignkey")
    op.drop_index("ix_issues_area_status", table_name="issues")
    op.drop_column("issues", "area_id")
    op.drop_index("ix_areas_rank", table_name="areas")
    op.drop_index("ix_areas_overall_score", table_name="areas")
    op.drop_table("areas")
