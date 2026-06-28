from typing import cast

from sqlalchemy import CheckConstraint, Index, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable, Table

from app.db.base import Base
from app.models import (
    AdminSession,
    Area,
    AreaScoreEvent,
    CivicOperationsReport,
    CommunityAction,
    Issue,
    IssueDraft,
    IssueUpdate,
    Mission,
    MissionAction,
)


def test_core_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {
        "admin_sessions",
        "areas",
        "area_score_events",
        "civic_operations_reports",
        "community_actions",
        "issue_drafts",
        "issue_updates",
        "issues",
        "mission_actions",
        "missions",
    }


def test_all_tables_compile_for_postgresql() -> None:
    for table in Base.metadata.sorted_tables:
        sql = str(CreateTable(table).compile(dialect=postgresql.dialect()))  # type: ignore[no-untyped-call]
        assert f"CREATE TABLE {table.name}" in sql


def test_community_action_has_actor_uniqueness_constraint() -> None:
    table = cast(Table, CommunityAction.__table__)
    constraints = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert "uq_community_actions_issue_action_actor" in constraints


def test_mission_action_has_null_safe_actor_uniqueness_indexes() -> None:
    table = cast(Table, MissionAction.__table__)
    indexes = {
        index.name
        for index in table.indexes
        if isinstance(index, Index) and index.unique
    }

    assert indexes >= {
        "uq_mission_actions_issue_actor",
        "uq_mission_actions_global_actor",
    }


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


def test_issue_coordinate_constraints_are_registered() -> None:
    issue_table = cast(Table, Issue.__table__)
    draft_table = cast(Table, IssueDraft.__table__)

    issue_constraints = {
        constraint.name
        for constraint in issue_table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    draft_constraints = {
        constraint.name
        for constraint in draft_table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert issue_constraints >= {
        "ck_issues_latitude_range",
        "ck_issues_longitude_range",
        "ck_issues_coordinates_complete",
    }
    assert draft_constraints >= {
        "ck_issue_drafts_latitude_range",
        "ck_issue_drafts_longitude_range",
        "ck_issue_drafts_coordinates_complete",
    }


def test_mission_progress_constraints_are_registered() -> None:
    table = cast(Table, Mission.__table__)
    constraints = [
        constraint for constraint in table.constraints if isinstance(constraint, CheckConstraint)
    ]

    assert {constraint.name for constraint in constraints} >= {
        "ck_missions_target_count_positive",
        "ck_missions_progress_count_non_negative",
        "ck_missions_progress_not_above_target",
    }


def test_expected_models_use_uuid_primary_keys() -> None:
    for model in (
        IssueDraft,
        Issue,
        IssueUpdate,
        CommunityAction,
        AdminSession,
        CivicOperationsReport,
        Area,
        AreaScoreEvent,
        Mission,
        MissionAction,
    ):
        table = cast(Table, model.__table__)
        assert [column.name for column in table.primary_key.columns] == ["id"]
