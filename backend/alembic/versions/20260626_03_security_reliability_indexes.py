"""Add indexes for security and reliability workflows.

Revision ID: 20260626_03
Revises: 20260625_02
Create Date: 2026-06-26
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260626_03"
down_revision: str | None = "20260625_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_community_actions_actor_created",
        "community_actions",
        ["actor_hash", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_issues_admin_updated",
        "issues",
        ["updated_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_issues_priority_queue",
        "issues",
        ["severity", "status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_issues_priority_queue", table_name="issues")
    op.drop_index("ix_issues_admin_updated", table_name="issues")
    op.drop_index("ix_community_actions_actor_created", table_name="community_actions")
