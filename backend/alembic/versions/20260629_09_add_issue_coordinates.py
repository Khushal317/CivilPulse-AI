"""Add issue coordinates.

Revision ID: 20260629_09
Revises: 20260628_08
Create Date: 2026-06-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260629_09"
down_revision: str | None = "20260628_08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _add_coordinate_columns("issue_drafts")
    _add_coordinate_columns("issues")


def downgrade() -> None:
    _drop_coordinate_columns("issues")
    _drop_coordinate_columns("issue_drafts")


def _add_coordinate_columns(table_name: str) -> None:
    op.add_column(table_name, sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column(table_name, sa.Column("longitude", sa.Float(), nullable=True))
    op.create_check_constraint(
        f"ck_{table_name}_latitude_range",
        table_name,
        "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
    )
    op.create_check_constraint(
        f"ck_{table_name}_longitude_range",
        table_name,
        "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
    )
    op.create_check_constraint(
        f"ck_{table_name}_coordinates_complete",
        table_name,
        "(latitude IS NULL AND longitude IS NULL) OR "
        "(latitude IS NOT NULL AND longitude IS NOT NULL)",
    )


def _drop_coordinate_columns(table_name: str) -> None:
    op.drop_constraint(f"ck_{table_name}_coordinates_complete", table_name, type_="check")
    op.drop_constraint(f"ck_{table_name}_longitude_range", table_name, type_="check")
    op.drop_constraint(f"ck_{table_name}_latitude_range", table_name, type_="check")
    op.drop_column(table_name, "longitude")
    op.drop_column(table_name, "latitude")
