"""Add validated image media types.

Revision ID: 20260625_02
Revises: 20260624_01
Create Date: 2026-06-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260625_02"
down_revision: str | None = "20260624_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "issue_drafts",
        sa.Column(
            "image_mime",
            sa.String(length=50),
            server_default="image/jpeg",
            nullable=False,
        ),
    )
    op.add_column(
        "issues",
        sa.Column(
            "image_mime",
            sa.String(length=50),
            server_default="image/jpeg",
            nullable=False,
        ),
    )
    op.alter_column("issue_drafts", "image_mime", server_default=None)
    op.alter_column("issues", "image_mime", server_default=None)


def downgrade() -> None:
    op.drop_column("issues", "image_mime")
    op.drop_column("issue_drafts", "image_mime")
