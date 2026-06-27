"""Add area score events.

Revision ID: 20260627_06
Revises: 20260627_05
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import context, op

revision: str = "20260627_06"
down_revision: str | None = "20260627_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCORE_KEYS = (
    "overall",
    "infrastructure",
    "cleanliness",
    "safety",
    "participation",
    "responsiveness",
    "environment",
)


def upgrade() -> None:
    op.create_table(
        "area_score_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("area_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("related_issue_id", sa.Uuid(), nullable=True),
        sa.Column("related_mission_id", sa.Uuid(), nullable=True),
        sa.Column("score_key", sa.String(length=14), nullable=False),
        sa.Column("score_change", sa.Integer(), nullable=False),
        sa.Column("previous_score", sa.Integer(), nullable=False),
        sa.Column("new_score", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"score_key IN {SCORE_KEYS!r}",
            name="ck_area_score_events_area_score_key",
        ),
        sa.ForeignKeyConstraint(
            ["area_id"],
            ["areas.id"],
            name="fk_area_score_events_area_id_areas",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["related_issue_id"],
            ["issues.id"],
            name="fk_area_score_events_related_issue_id_issues",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_area_score_events"),
    )
    op.create_index(
        "ix_area_score_events_area_created",
        "area_score_events",
        ["area_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_area_score_events_score_key",
        "area_score_events",
        ["score_key"],
        unique=False,
    )
    if not context.is_offline_mode():
        _rank_existing_areas()


def _rank_existing_areas() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE areas
            SET rank = ranked.rank
            FROM (
                SELECT
                    id,
                    row_number() OVER (
                        ORDER BY overall_score DESC, name ASC, id ASC
                    ) AS rank
                FROM areas
            ) AS ranked
            WHERE areas.id = ranked.id
            """
        ),
    )


def downgrade() -> None:
    op.drop_index("ix_area_score_events_score_key", table_name="area_score_events")
    op.drop_index("ix_area_score_events_area_created", table_name="area_score_events")
    op.drop_table("area_score_events")
