from typing import cast

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable, Table

from app.db.base import Base
from app.models import AdminSession, CommunityAction, Issue, IssueDraft, IssueUpdate


def test_core_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {
        "admin_sessions",
        "community_actions",
        "issue_drafts",
        "issue_updates",
        "issues",
    }


def test_all_tables_compile_for_postgresql() -> None:
    for table in Base.metadata.sorted_tables:
        sql = str(CreateTable(table).compile(dialect=postgresql.dialect()))
        assert f"CREATE TABLE {table.name}" in sql


def test_community_action_has_actor_uniqueness_constraint() -> None:
    table = cast(Table, CommunityAction.__table__)
    constraints = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert "uq_community_actions_issue_action_actor" in constraints


def test_enum_columns_create_database_checks() -> None:
    table = cast(Table, Issue.__table__)
    constraints = [
        constraint for constraint in table.constraints if isinstance(constraint, CheckConstraint)
    ]

    assert {constraint.name for constraint in constraints} >= {
        "ck_issues_issue_category",
        "ck_issues_issue_severity",
        "ck_issues_issue_status",
        "ck_issues_urgency_level",
    }


def test_expected_models_use_uuid_primary_keys() -> None:
    for model in (IssueDraft, Issue, IssueUpdate, CommunityAction, AdminSession):
        table = cast(Table, model.__table__)
        assert [column.name for column in table.primary_key.columns] == ["id"]
