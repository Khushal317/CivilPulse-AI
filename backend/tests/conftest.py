from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.db.migrations import CURRENT_DATABASE_REVISION
from app.db.session import get_db_session
from app.main import app


class ScalarResult:
    def scalar_one_or_none(self) -> str:
        return CURRENT_DATABASE_REVISION


class HealthyDatabaseSession:
    def execute(self, *_args: Any, **_kwargs: Any) -> ScalarResult:
        return ScalarResult()


def healthy_database_session() -> Generator[HealthyDatabaseSession]:
    yield HealthyDatabaseSession()


@pytest.fixture
def client() -> Generator[TestClient]:
    app.dependency_overrides[get_db_session] = healthy_database_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
