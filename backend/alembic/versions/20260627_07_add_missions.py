"""Add missions.

Revision ID: 20260627_07
Revises: 20260627_06
Create Date: 2026-06-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260627_07"
down_revision: str | None = "20260627_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MISSION_STATUSES = ("draft", "active", "completed", "expired")
MISSION_TYPES = ("verification", "fix_confirmation", "hotspot", "category", "volunteer")
MISSION_ACTION_TYPES = (
    "joined",
    "verified_issue",
    "confirmed_unresolved",
    "confirmed_fixed",
    "volunteered",
)
ISSUE_CATEGORIES = (
    "road_damage",
    "garbage_waste",
    "streetlight",
    "water_leakage",
    "drainage_sewage",
    "public_safety",
    "other",
)


def upgrade() -> None:
    op.create_table(
        "missions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("area_id", sa.Uuid(), nullable=False),
        sa.Column("mission_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=9), nullable=False),
        sa.Column("goal_description", sa.Text(), nullable=False),
        sa.Column("target_count", sa.Integer(), nullable=False),
        sa.Column("progress_count", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=True),
        sa.Column("reward_json", sa.JSON(), nullable=False),
        sa.Column("ai_reason", sa.Text(), nullable=False),
        sa.Column("linked_issue_ids_json", sa.JSON(), nullable=False),
        sa.Column("model_used", sa.String(length=120), nullable=True),
        sa.Column("raw_response_json", sa.JSON(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            f"mission_type IN {MISSION_TYPES!r}",
            name="ck_missions_mission_type",
        ),
        sa.CheckConstraint(
            f"status IN {MISSION_STATUSES!r}",
            name="ck_missions_mission_status",
        ),
        sa.CheckConstraint(
            f"category IN {ISSUE_CATEGORIES!r}",
            name="ck_missions_mission_issue_category",
        ),
        sa.CheckConstraint("target_count > 0", name="target_count_positive"),
        sa.CheckConstraint("progress_count >= 0", name="progress_count_non_negative"),
        sa.CheckConstraint("progress_count <= target_count", name="progress_not_above_target"),
        sa.ForeignKeyConstraint(
            ["area_id"],
            ["areas.id"],
            name="fk_missions_area_id_areas",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_missions"),
    )
    op.create_index("ix_missions_area_status", "missions", ["area_id", "status"])
    op.create_index("ix_missions_status_expires", "missions", ["status", "expires_at"])
    op.create_index("ix_missions_type_status", "missions", ["mission_type", "status"])

    op.create_table(
        "mission_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("mission_id", sa.Uuid(), nullable=False),
        sa.Column("issue_id", sa.Uuid(), nullable=True),
        sa.Column("action_type", sa.String(length=20), nullable=False),
        sa.Column("actor_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"action_type IN {MISSION_ACTION_TYPES!r}",
            name="ck_mission_actions_mission_action_type",
        ),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["issues.id"],
            name="fk_mission_actions_issue_id_issues",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["mission_id"],
            ["missions.id"],
            name="fk_mission_actions_mission_id_missions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_mission_actions"),
    )
    op.create_index(
        "uq_mission_actions_issue_actor",
        "mission_actions",
        ["mission_id", "issue_id", "action_type", "actor_hash"],
        unique=True,
        postgresql_where=sa.text("issue_id IS NOT NULL"),
    )
    op.create_index(
        "uq_mission_actions_global_actor",
        "mission_actions",
        ["mission_id", "action_type", "actor_hash"],
        unique=True,
        postgresql_where=sa.text("issue_id IS NULL"),
    )
    op.create_index(
        "ix_mission_actions_actor_created",
        "mission_actions",
        ["actor_hash", "created_at"],
    )
    op.create_index(
        "ix_mission_actions_mission_type",
        "mission_actions",
        ["mission_id", "action_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_mission_actions_mission_type", table_name="mission_actions")
    op.drop_index("ix_mission_actions_actor_created", table_name="mission_actions")
    op.drop_index("uq_mission_actions_global_actor", table_name="mission_actions")
    op.drop_index("uq_mission_actions_issue_actor", table_name="mission_actions")
    op.drop_table("mission_actions")
    op.drop_index("ix_missions_type_status", table_name="missions")
    op.drop_index("ix_missions_status_expires", table_name="missions")
    op.drop_index("ix_missions_area_status", table_name="missions")
    op.drop_table("missions")
