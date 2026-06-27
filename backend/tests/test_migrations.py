import os
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command

EXPECTED_TABLES = {
    "admin_sessions",
    "alembic_version",
    "areas",
    "area_score_events",
    "civic_operations_reports",
    "community_actions",
    "issue_drafts",
    "issue_updates",
    "issues",
}


def alembic_config(database_url: str) -> Config:
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def test_initial_migration_generates_postgresql_sql(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://civicpulse:test@localhost:5432/civicpulse_test",
    )
    command.upgrade(alembic_config(os.environ["DATABASE_URL"]), "head", sql=True)

    sql = capsys.readouterr().out
    assert "CREATE TABLE area_score_events" in sql
    assert "CREATE TABLE areas" in sql
    assert "CREATE TABLE civic_operations_reports" in sql
    assert "CREATE TABLE issues" in sql
    assert "uq_community_actions_issue_action_actor" in sql
    assert "DROP TABLE issues" not in sql


def test_initial_migration_generates_downgrade_sql(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://civicpulse:test@localhost:5432/civicpulse_test",
    )
    command.downgrade(
        alembic_config(os.environ["DATABASE_URL"]),
        "head:base",
        sql=True,
    )

    sql = capsys.readouterr().out
    assert "DROP TABLE area_score_events" in sql
    assert "DROP TABLE areas" in sql
    assert "DROP TABLE civic_operations_reports" in sql
    assert "DROP TABLE issues" in sql
    assert "DROP TABLE issue_drafts" in sql


@pytest.mark.postgres
def test_upgrade_and_downgrade_on_postgresql(monkeypatch: pytest.MonkeyPatch) -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is not configured")
    if "_test" not in database_url:
        pytest.fail("TEST_DATABASE_URL must point to a dedicated database containing '_test'")
    monkeypatch.setenv("DATABASE_URL", database_url)

    config = alembic_config(database_url)

    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    try:
        assert set(inspect(engine).get_table_names()) >= EXPECTED_TABLES
    finally:
        engine.dispose()

    command.downgrade(config, "base")
    engine = create_engine(database_url)
    try:
        assert not (EXPECTED_TABLES - {"alembic_version"}) & set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
