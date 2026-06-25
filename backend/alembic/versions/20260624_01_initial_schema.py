"""Create CivicPulse core tables.

Revision ID: 20260624_01
Revises:
Create Date: 2026-06-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260624_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

issue_category = sa.Enum(
    "road_damage",
    "garbage_waste",
    "streetlight",
    "water_leakage",
    "drainage_sewage",
    "public_safety",
    "other",
    name="issue_category",
    native_enum=False,
    create_constraint=True,
)
issue_severity = sa.Enum(
    "low",
    "medium",
    "high",
    "critical",
    name="issue_severity",
    native_enum=False,
    create_constraint=True,
)
urgency_level = sa.Enum(
    "routine",
    "soon",
    "urgent",
    "immediate",
    name="urgency_level",
    native_enum=False,
    create_constraint=True,
)
issue_status = sa.Enum(
    "reported",
    "community_verified",
    "escalated",
    "in_progress",
    "resolved",
    "rejected",
    name="issue_status",
    native_enum=False,
    create_constraint=True,
)
issue_update_from_status = sa.Enum(
    "reported",
    "community_verified",
    "escalated",
    "in_progress",
    "resolved",
    "rejected",
    name="issue_update_from_status",
    native_enum=False,
    create_constraint=True,
)
issue_update_to_status = sa.Enum(
    "reported",
    "community_verified",
    "escalated",
    "in_progress",
    "resolved",
    "rejected",
    name="issue_update_to_status",
    native_enum=False,
    create_constraint=True,
)
community_action_type = sa.Enum(
    "saw_this_too",
    "still_unresolved",
    "fixed",
    "incorrect",
    name="community_action_type",
    native_enum=False,
    create_constraint=True,
)
update_actor_type = sa.Enum(
    "system",
    "admin",
    name="update_actor_type",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "issue_drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("original_description", sa.Text(), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("landmark", sa.String(length=255), nullable=True),
        sa.Column("citizen_name", sa.String(length=120), nullable=True),
        sa.Column("citizen_contact", sa.String(length=255), nullable=True),
        sa.Column("urgency_note", sa.Text(), nullable=True),
        sa.Column("image_key", sa.String(length=512), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("category", issue_category, nullable=True),
        sa.Column("severity", issue_severity, nullable=True),
        sa.Column("urgency_level", urgency_level, nullable=True),
        sa.Column("urgency_reason", sa.Text(), nullable=True),
        sa.Column("suggested_department", sa.String(length=180), nullable=True),
        sa.Column("safety_risk", sa.Text(), nullable=True),
        sa.Column("citizen_explanation", sa.Text(), nullable=True),
        sa.Column("suggested_next_action", sa.Text(), nullable=True),
        sa.Column("ai_model", sa.String(length=120), nullable=True),
        sa.Column("prompt_version", sa.String(length=50), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name="pk_issue_drafts"),
        sa.UniqueConstraint("image_key", name="uq_issue_drafts_image_key"),
    )
    op.create_index(
        "ix_issue_drafts_expires_unpublished",
        "issue_drafts",
        ["expires_at", "published_at"],
        unique=False,
    )

    op.create_table(
        "issues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_reference", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("original_description", sa.Text(), nullable=False),
        sa.Column("ai_summary", sa.Text(), nullable=False),
        sa.Column("category", issue_category, nullable=False),
        sa.Column("severity", issue_severity, nullable=False),
        sa.Column("urgency_level", urgency_level, nullable=False),
        sa.Column("urgency_reason", sa.Text(), nullable=False),
        sa.Column("suggested_department", sa.String(length=180), nullable=False),
        sa.Column("safety_risk", sa.Text(), nullable=False),
        sa.Column("citizen_explanation", sa.Text(), nullable=False),
        sa.Column("suggested_next_action", sa.Text(), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("landmark", sa.String(length=255), nullable=True),
        sa.Column("image_key", sa.String(length=512), nullable=False),
        sa.Column("status", issue_status, nullable=False),
        sa.Column("citizen_name", sa.String(length=120), nullable=True),
        sa.Column("citizen_contact", sa.String(length=255), nullable=True),
        sa.Column("ai_model", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name="pk_issues"),
        sa.UniqueConstraint("image_key", name="uq_issues_image_key"),
        sa.UniqueConstraint("public_reference", name="uq_issues_public_reference"),
    )
    op.create_index(
        "ix_issues_category_severity",
        "issues",
        ["category", "severity"],
        unique=False,
    )
    op.create_index("ix_issues_location_search", "issues", ["location"], unique=False)
    op.create_index(
        "ix_issues_tracker_newest",
        "issues",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "admin_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_admin_sessions"),
        sa.UniqueConstraint("token_hash", name="uq_admin_sessions_token_hash"),
    )
    op.create_index(
        "ix_admin_sessions_active",
        "admin_sessions",
        ["expires_at", "revoked_at"],
        unique=False,
    )

    op.create_table(
        "community_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("issue_id", sa.Uuid(), nullable=False),
        sa.Column("action_type", community_action_type, nullable=False),
        sa.Column("actor_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["issues.id"],
            name="fk_community_actions_issue_id_issues",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_community_actions"),
        sa.UniqueConstraint(
            "issue_id",
            "action_type",
            "actor_hash",
            name="uq_community_actions_issue_action_actor",
        ),
    )
    op.create_index(
        "ix_community_actions_issue_type",
        "community_actions",
        ["issue_id", "action_type"],
        unique=False,
    )

    op.create_table(
        "issue_updates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("issue_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", issue_update_from_status, nullable=True),
        sa.Column("to_status", issue_update_to_status, nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("actor_type", update_actor_type, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["issue_id"],
            ["issues.id"],
            name="fk_issue_updates_issue_id_issues",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_issue_updates"),
    )
    op.create_index(
        "ix_issue_updates_timeline",
        "issue_updates",
        ["issue_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_issue_updates_timeline", table_name="issue_updates")
    op.drop_table("issue_updates")
    op.drop_index("ix_community_actions_issue_type", table_name="community_actions")
    op.drop_table("community_actions")
    op.drop_index("ix_admin_sessions_active", table_name="admin_sessions")
    op.drop_table("admin_sessions")
    op.drop_index("ix_issues_tracker_newest", table_name="issues")
    op.drop_index("ix_issues_location_search", table_name="issues")
    op.drop_index("ix_issues_category_severity", table_name="issues")
    op.drop_table("issues")
    op.drop_index("ix_issue_drafts_expires_unpublished", table_name="issue_drafts")
    op.drop_table("issue_drafts")
