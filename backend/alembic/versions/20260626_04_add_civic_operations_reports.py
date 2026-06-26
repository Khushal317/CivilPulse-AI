"""Add civic operations reports.

Revision ID: 20260626_04
Revises: 20260626_03
Create Date: 2026-06-26
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260626_04"
down_revision: str | None = "20260626_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "civic_operations_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("total_issues_analyzed", sa.Integer(), nullable=False),
        sa.Column("model_used", sa.String(length=120), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("urgent_issues_json", sa.JSON(), nullable=False),
        sa.Column("duplicate_clusters_json", sa.JSON(), nullable=False),
        sa.Column("area_hotspots_json", sa.JSON(), nullable=False),
        sa.Column("department_priorities_json", sa.JSON(), nullable=False),
        sa.Column("escalation_messages_json", sa.JSON(), nullable=False),
        sa.Column("predicted_risks_json", sa.JSON(), nullable=False),
        sa.Column("raw_response_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_civic_operations_reports"),
    )
    op.create_index(
        "ix_civic_operations_reports_generated_at",
        "civic_operations_reports",
        ["generated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_civic_operations_reports_generated_at",
        table_name="civic_operations_reports",
    )
    op.drop_table("civic_operations_reports")
