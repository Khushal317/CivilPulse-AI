"""Add duplicate issue lifecycle.

Revision ID: 20260628_08
Revises: 20260627_07
Create Date: 2026-06-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260628_08"
down_revision: str | None = "20260627_07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ISSUE_STATUSES = (
    "reported",
    "community_verified",
    "escalated",
    "in_progress",
    "resolved",
    "rejected",
    "duplicate",
)
PREVIOUS_ISSUE_STATUSES = ISSUE_STATUSES[:-1]


def upgrade() -> None:
    _replace_issue_status_constraint("issues", "issue_status", ISSUE_STATUSES)
    _replace_issue_status_constraint(
        "issue_updates",
        "issue_update_from_status",
        ISSUE_STATUSES,
    )
    _replace_issue_status_constraint(
        "issue_updates",
        "issue_update_to_status",
        ISSUE_STATUSES,
    )
    op.add_column("issues", sa.Column("duplicate_of_issue_id", sa.Uuid(), nullable=True))
    op.add_column(
        "issues",
        sa.Column("duplicate_marked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_issues_duplicate_of_issue_id_issues",
        "issues",
        "issues",
        ["duplicate_of_issue_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_issues_duplicate_retention",
        "issues",
        ["status", "duplicate_marked_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_issues_duplicate_retention", table_name="issues")
    op.drop_constraint(
        "fk_issues_duplicate_of_issue_id_issues",
        "issues",
        type_="foreignkey",
    )
    op.drop_column("issues", "duplicate_marked_at")
    op.drop_column("issues", "duplicate_of_issue_id")
    _replace_issue_status_constraint("issues", "issue_status", PREVIOUS_ISSUE_STATUSES)
    _replace_issue_status_constraint(
        "issue_updates",
        "issue_update_from_status",
        PREVIOUS_ISSUE_STATUSES,
    )
    _replace_issue_status_constraint(
        "issue_updates",
        "issue_update_to_status",
        PREVIOUS_ISSUE_STATUSES,
    )


def _replace_issue_status_constraint(
    table_name: str,
    constraint_name: str,
    statuses: tuple[str, ...],
) -> None:
    op.drop_constraint(constraint_name, table_name, type_="check")
    op.create_check_constraint(
        constraint_name,
        table_name,
        f"status IN {statuses!r}" if table_name == "issues" else _update_status_sql(
            constraint_name,
            statuses,
        ),
    )


def _update_status_sql(constraint_name: str, statuses: tuple[str, ...]) -> str:
    column = "from_status" if constraint_name.endswith("from_status") else "to_status"
    if column == "from_status":
        return f"{column} IS NULL OR {column} IN {statuses!r}"
    return f"{column} IN {statuses!r}"
