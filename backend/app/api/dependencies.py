from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.repositories.admin import SQLAlchemyAdminSessionRepository
from app.repositories.admin_issues import SQLAlchemyAdminIssueRepository
from app.repositories.issues import SQLAlchemyIssueRepository
from app.repositories.reports import SQLAlchemyReportRepository
from app.services.admin import AdminService
from app.services.admin_auth import AdminAuthService, get_login_rate_limiter
from app.services.ai import CivicIssueAnalyzer, get_civic_issue_analyzer
from app.services.issues import IssueService
from app.services.rate_limit import InMemoryRateLimiter
from app.services.reports import ReportService
from app.services.storage import ImageStorage, get_image_storage

DatabaseDependency = Annotated[Session, Depends(get_db_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]
StorageDependency = Annotated[ImageStorage, Depends(get_image_storage)]
AnalyzerDependency = Annotated[CivicIssueAnalyzer, Depends(get_civic_issue_analyzer)]


@lru_cache
def build_report_analysis_rate_limiter(limit: int, window_minutes: int) -> InMemoryRateLimiter:
    return InMemoryRateLimiter(
        limit=limit,
        window_minutes=window_minutes,
        code="report_analysis_rate_limited",
        message="Too many report analyses were requested. Please try again later.",
    )


def get_report_analysis_rate_limiter(
    settings: SettingsDependency,
) -> InMemoryRateLimiter:
    return build_report_analysis_rate_limiter(
        settings.report_analysis_rate_limit,
        settings.report_analysis_rate_window_minutes,
    )


ReportAnalysisRateLimiterDependency = Annotated[
    InMemoryRateLimiter,
    Depends(get_report_analysis_rate_limiter),
]


def get_report_service(
    session: DatabaseDependency,
    storage: StorageDependency,
    analyzer: AnalyzerDependency,
    settings: SettingsDependency,
) -> ReportService:
    return ReportService(
        repository=SQLAlchemyReportRepository(session),
        storage=storage,
        analyzer=analyzer,
        settings=settings,
    )


ReportServiceDependency = Annotated[ReportService, Depends(get_report_service)]


def get_issue_service(
    session: DatabaseDependency,
    settings: SettingsDependency,
) -> IssueService:
    return IssueService(
        repository=SQLAlchemyIssueRepository(session),
        settings=settings,
    )


IssueServiceDependency = Annotated[IssueService, Depends(get_issue_service)]


def get_admin_auth_service(
    session: DatabaseDependency,
    settings: SettingsDependency,
) -> AdminAuthService:
    return AdminAuthService(
        repository=SQLAlchemyAdminSessionRepository(session),
        settings=settings,
        rate_limiter=get_login_rate_limiter(),
    )


AdminAuthServiceDependency = Annotated[AdminAuthService, Depends(get_admin_auth_service)]


def get_admin_service(session: DatabaseDependency) -> AdminService:
    return AdminService(repository=SQLAlchemyAdminIssueRepository(session))


AdminServiceDependency = Annotated[AdminService, Depends(get_admin_service)]
